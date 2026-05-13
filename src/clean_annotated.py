import argparse
import io
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_PATH = BASE_DIR / "data" / "source_items_annotated.json"
OUT_PATH = BASE_DIR / "data" / "source_items_clean.json"


# Настройка фильтрации, поскольку результаты вопросы получаются плохого качества

#1 Стоп-слова в начале concept - всякие местоимения, союзы
BAD_STARTS = re.compile(
    r'^(это|этот|эта|эти|такой|такая|такое|такие|данный|данная|'
    r'который|которая|которое|которые|которых|которого|которому|'
    r'то |если |когда |пусть |тогда |поскольку |также |притом |'
    r'что |так |иногда |часто |обычно |просто |именно |'
    r'наибольшее |наименьшее |некоторое |любое |каждое |'
    r'все |всё |сам |само |самом |правой |левой |этого |того |' 
    r'в |на |из |для |с |к |о |об |по |при |за |до |над |под )',
    re.IGNORECASE,
)

CONTEXT_DEPENDENT = re.compile(
    r'\b(этого|того|данного|соотношения|рисунка|таблицы|примера|вышеуказанного|нижеследующего)\b',
    re.IGNORECASE,
)
# мусорная структура - слишком много мелких слов
def is_structural_junk(concept: str) -> bool:
    words = concept.strip().split()
    if not words: return True
    
    short_words = [w for w in words if len(w) <= 2]
    if len(words) >= 3 and len(short_words) >= 2:
        return True
    return False

BAD_INNER = re.compile(
    r'\s(или|если|либо|поскольку|потому|хотя|чтобы|'
    r'тесно|часто|обычно|просто|именно|также|лишь|'
    r'и обозначается|и используется|и применяется)\s',
    re.IGNORECASE,
)

BAD_ENDS = re.compile(
    r'\s(и|или|а|но|то|что|как|это|тесно|часто|обычно|также|лишь|'
    r'обозначается|используется|применяется|называется|является)$',
    re.IGNORECASE,
)

BAD_SENTENCE = re.compile(
    r'\(\d+/\d+\)|п\.\s*\d+\.\d+|\bсм\.\s*п\b',
    re.IGNORECASE,
)

KNOWN_SHORT_TERMS = {
    'граф', 'сеть', 'цикл', 'путь', 'лес', 'дерево', 'корень',
    'ребро', 'вершина', 'поток', 'разрез', 'клика', 'доля',
    'матрица', 'вектор', 'базис', 'ранг', 'ядро', 'образ',
    'группа', 'кольцо', 'поле', 'модуль', 'идеал', 'тело',
    'алфавит', 'слово', 'язык', 'грамматика', 'автомат',
    'функция', 'предикат', 'формула', 'терм', 'литерал',
    'длина', 'мощность', 'степень', 'порядок', 'индекс',
    'отношение', 'операция', 'алгебра', 'решётка', 'полурешётка',
    'множество', 'класс', 'семейство', 'система', 'структура',
    'алгоритм', 'задача', 'проблема', 'сложность',
    'паросочетание', 'покрытие', 'раскраска',
}

# кейс когда концепт состоит только из одного плохого слова 
SINGLE_BAD_WORDS = {
    'иногда', 'также', 'часто', 'обычно', 'просто', 'именно',
    'всегда', 'никогда', 'редко', 'лишь', 'только', 'даже',
    'здесь', 'там', 'так', 'вот', 'уже', 'ещё', 'уж',
}

# кейс когда начинается с маленькой буквы и не является продолжением термина
# то есть regex взял середину предложения
STARTS_LOWERCASE_RU = re.compile(r'^[а-яё]')

INDIRECT_CASE_ENDING = re.compile(
    r'[а-яё](ым|ой|ем|ом|ей|ых|ых|им|их|ую|юю|ая|яя)$',
    re.IGNORECASE,
)


def is_single_word_inflected(concept: str) -> bool:
    words = concept.strip().split()
    if len(words) != 1:
        return False
    word = words[0].lower()
    if word in KNOWN_SHORT_TERMS:
        return False
    return bool(INDIRECT_CASE_ENDING.search(word))



def check_record(r: dict) -> list[str]:
    reasons = []
    c1 = r.get('concept1', '').strip()
    c2 = r.get('concept2', '').strip()

    for label, concept in [('concept1', c1), ('concept2', c2)]:
        
        if CONTEXT_DEPENDENT.search(concept):
            reasons.append(f'{label} привязано к контексту текста: «{concept}»')
            
        if is_structural_junk(concept):
            reasons.append(f'{label} похоже на фрагмент предложения: «{concept}»')

    return reasons

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src',    default=str(SRC_PATH))
    parser.add_argument('--out',    default=str(OUT_PATH))
    parser.add_argument('--report', action='store_true',
                        help='Только показать что будет удалено, не сохранять')
    args = parser.parse_args()

    src_path = Path(args.src)
    out_path = Path(args.out)

    records = json.loads(src_path.read_text(encoding='utf-8'))
    print(f'Загружено записей: {len(records)}')

    good, bad = [], []

    for r in records:
        reasons = check_record(r)
        if reasons:
            bad.append((r, reasons))
        else:
            good.append(r)

    print(f'  хороших записей: {len(good)}')
    print(f'  мусорных:        {len(bad)}')

    if args.report:
        print(f'\n{"=" * 60}')
        print('ЗАПИСИ ДЛЯ УДАЛЕНИЯ:')
        for r, reasons in bad:
            print(f'\n  c1: «{r["concept1"]}»')
            print(f'  c2: «{r["concept2"]}»')
            print(f'  rel: {r["relation"]}')
            for reason in reasons:
                print(f'  ! {reason}')
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(good, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    print(' To launcg in terminal:\n python src/generate_questions.py --source data/source_items_clean.json')


if __name__ == '__main__':
    main()