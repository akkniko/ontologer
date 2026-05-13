"""
auto_annotate.py
Автоматически фильтрует source_items.json и заполняет
concept1 / concept2 / relation по паттернам
без использования LLM-ок 

"""

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
SRC_PATH = BASE_DIR / "data" / "source_items.json"
OUT_PATH = BASE_DIR / "data" / "source_items_annotated.json"



def preprocess(s: str) -> str:
    s = re.sub(r'([а-яёА-ЯЁa-zA-Z])-\s+([а-яёА-ЯЁa-zA-Z])', r'\1\2', s)
    return re.sub(r'\s+', ' ', s).strip()


MATH_CHARS  = re.compile(r'[∈∉∅⩽⩾∀∃∨∧¬→↔∩∪⊆⊂⊃±×÷√∞∑∏⟨⟩]')
FORMULA     = re.compile(r':=|\{[^}]{0,60}\||\(cid:\d+\)|\\[a-zA-Z]+')
LATIN_LONG  = re.compile(r'[A-Za-z]{5,}')
GLUED_CYR   = re.compile(r'[а-яёА-ЯЁ]{20,}')   
DIGITS_LONG = re.compile(r'\d{4,}')
MIN_CHARS, MAX_CHARS = 25, 280


def is_junk(s: str) -> bool:
    if len(s) < MIN_CHARS or len(s) > MAX_CHARS:
        return True
    for pat in (MATH_CHARS, FORMULA, LATIN_LONG, GLUED_CYR, DIGITS_LONG):
        if pat.search(s):
            return True
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return True
    cyr_ratio = sum(1 for c in letters if '\u0400' <= c <= '\u04FF') / len(letters)
    return cyr_ratio < 0.55


CYR_WORD = r'[А-ЯЁа-яё][а-яёА-ЯЁ\-]*'

C = rf'({CYR_WORD}(?:\s+{CYR_WORD}){{0,2}})'

STOP_CONCEPTS = {
    'он', 'она', 'оно', 'они', 'это', 'этот', 'эта', 'эти',
    'такой', 'такая', 'такое', 'такие', 'данный', 'данная',
    'который', 'которая', 'которое', 'которые',
    'следующий', 'следующая', 'каждый', 'любой', 'некоторый',
    'пример', 'случай', 'способ', 'вид', 'тип', 'число',
    'утверждение', 'свойство', 'понятие', 'результат',
    'пусть', 'тогда', 'если', 'поэтому', 'таким', 'таким образом',
    'часть', 'части', 'сторона', 'стороны', 'пункт', 'параграф', 
    'уравнение', 'соотношение', 'выражение', 'доказательство',
    'утверждение', 'условие', 'результат', 'начало', 'конец'
    
}

# Слова шумы 
BAD_STARTS = re.compile(
    r'^(при\s|в\s|на\s|из\s|для\s|с\s|со\s|к\s|о\s|об\s|'
    r'пусть|тогда|если|поэтому|таким|таким образом|итак|далее)',
    re.IGNORECASE,
)

RAW = [

    # НАСЛЕДОВАНИЕ 
    # "X является частным случаем Y"
    (rf'(?P<c1>{C})\s+является\s+частным\s+случаем\s+(?P<c2>{C})',
     'наследование'),

    # "X — частный случай Y"
    (rf'(?P<c1>{C})\s+[—–]\s+частный\s+случай\s+(?P<c2>{C})',
     'наследование'),

    # "X является подвидом / подтипом / разновидностью Y"
    (rf'(?P<c1>{C})\s+является\s+(?:подвидом|подтипом|разновидностью|подклассом)\s+(?P<c2>{C})',
     'наследование'),

    # АГРЕГАЦИЯ 
    # "X состоит из Y"
    (rf'(?P<c1>{C})\s+состоит\s+из\s+(?P<c2>{C})',
     'агрегация'),

    # "X включает (в себя) Y"
    (rf'(?P<c1>{C})\s+включает(?:\s+в\s+себя)?\s+(?P<c2>{C})',
     'агрегация'),

    # "элементами X являются Y"
    (rf'элементами\s+(?P<c1>{C})\s+(?:являются|служат)\s+(?P<c2>{C})',
     'агрегация'),

    # АССОЦИАЦИЯ или же определеня 
    # "X называется Y"
    (rf'(?P<c1>{C})\s+называется\s+(?:также\s+)?(?P<c2>{C})',
     'ассоциация'),

    # "X называют Y"
    (rf'(?P<c1>{C})\s+называют\s+(?:также\s+)?(?P<c2>{C})',
     'ассоциация'),

    # "X применяется для Y" / "X используется для Y"
    (rf'(?P<c1>{C})\s+(?:применяется|используется)\s+для\s+(?P<c2>{C})',
     'ассоциация'),

    # "X определяется через Y"
    (rf'(?P<c1>{C})\s+(?:определяется|выражается|задаётся|задается)\s+через\s+(?P<c2>{C})',
     'ассоциация'),

    # "X связан(о/а/ы/.) с Y"
    (rf'(?P<c1>{C})\s+(?:связано|связан|связана|связаны)\s+с\s+(?P<c2>{C})',
     'ассоциация'),
]

PATTERNS = [(re.compile(p, re.IGNORECASE), rel) for p, rel in RAW]


TRAILING = re.compile(
    r'\s+(?:и|или|а|но|если|то|как|где|когда|который|которая|которое|которые|'
    r'для|с|со|в|на|по|из|к|от|до|над|под|при|за|через|между|у|о|об|'
    r'это|не|ни|же|бы|ли|также)\s*$',
    re.IGNORECASE,
)


def clean_concept(text: str) -> str:
    text = text.strip().rstrip('.,;:(')
    text = TRAILING.sub('', text).strip().rstrip('.,;:(')
    return text


def try_annotate(sentence: str) -> tuple[str, str, str, float]:
    for pat, relation in PATTERNS:
        m = pat.search(sentence)
        if not m:
            continue

        c1 = clean_concept(m.group('c1'))
        c2 = clean_concept(m.group('c2'))

        if not c1 or not c2:
            continue

        if not re.search(r'[А-ЯЁа-яё]{3,}', c1):
            continue
        if not re.search(r'[А-ЯЁа-яё]{3,}', c2):
            continue

            #стоп-слова
        if c1.lower() in STOP_CONCEPTS or c2.lower() in STOP_CONCEPTS:
            continue
        if BAD_STARTS.match(c1) or BAD_STARTS.match(c2):
            continue

        if len(c1.split()) > 4 or len(c2.split()) > 4:
            continue

        conf = 1.0 if (len(c1.split()) > 1 and len(c2.split()) > 1) else 0.7

        return c1, c2, relation, conf

    return '', '', '', 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src',    default=str(SRC_PATH))
    parser.add_argument('--out',    default=str(OUT_PATH))
    parser.add_argument('--review', action='store_true')
    parser.add_argument('--min-confidence', type=float, default=0.0)
    args = parser.parse_args()

    raw = json.loads(Path(args.src).read_text(encoding='utf-8'))
    print(f'Загружено записей: {len(raw)}')

    stats = {'junk': 0, 'no_match': 0, 'low_conf': 0, 'manual': 0, 'auto': 0}
    result = []

    for item in raw:
        s = preprocess(item['sentence'])

        if item.get('concept1') and item.get('concept2') and item.get('relation'):
            result.append({**item, 'sentence': s, 'confidence': 1.0, 'auto': False})
            stats['manual'] += 1
            continue

        if is_junk(s):
            stats['junk'] += 1
            continue

        c1, c2, relation, conf = try_annotate(s)

        if not c1:
            stats['no_match'] += 1
            continue

        if conf < args.min_confidence:
            stats['low_conf'] += 1
            continue

        stats['auto'] += 1
        result.append({
            'sentence': s, 'concept1': c1, 'concept2': c2,
            'relation': relation, 'confidence': conf, 'auto': True,
        })

    total = stats['manual'] + stats['auto']
    print(f'  мусор отфильтрован:   {stats["junk"]}')
    print(f'  паттерн не найден:    {stats["no_match"]}')
    print(f'  ниже порога:          {stats["low_conf"]}')
    print(f'  ручная разметка:      {stats["manual"]}')
    print(f'  авторазметка:         {stats["auto"]}')
    print(f'  итого оставлено:      {total}')

    if args.review:
        print(f'\n{"─"*60}')
        for r in result:
            if not r.get('auto'):
                continue
            print(f'\n[conf={r["confidence"]:.1f}]  {r["sentence"]}')
            print(f'  c1  = «{r["concept1"]}»')
            print(f'  c2  = «{r["concept2"]}»')
            print(f'  rel = {r["relation"]}')
        return

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(f'\nСохранено: {out_path}')
  
if __name__ == '__main__':
    main()