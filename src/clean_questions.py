"""
clean_questions.py - обработка questions.json(если вопросы были сгенерированы на основе трейн датасета):
происхдит дедупликация, фильтрация вопросов.

Запуск:
    python src/clean_questions.py
    python src/clean_questions.py --src data/questions.json --out data/questions_clean.json
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
SRC_PATH = BASE_DIR / "data" / "questions.json"
OUT_PATH = BASE_DIR / "data" / "questions_clean.json"

ADJECTIVE_ONLY = re.compile(
    r'^[А-ЯЁа-яё][а-яё]+(ное|ная|ный|ные|ого|ому|ным|ной|ого|'
    r'щий|щая|щее|щие|щего|щему|'
    r'тый|тая|тое|тые|того|тому|'
    r'вый|вая|вое|вые|вого|вому)$',
    re.IGNORECASE,
)

ALLOWED_ADJ_TERMS = {
    'булево', 'булева', 'булевой', 'булевых', 'булевы',
    'конечное', 'конечная', 'конечный', 
    'пустое', 'пустой', 'пустая',
    'транзитивное', 'рефлексивное', 'симметричное',
    'линейное', 'частичное', 'полное',
}


def is_bad_concept(concept: str) -> bool:
    words = concept.strip().split()
    if len(words) != 1:
        return False  
    word = words[0].lower()
    if word in ALLOWED_ADJ_TERMS:
        return False
    return bool(ADJECTIVE_ONLY.match(concept.strip()))

BAD_SOURCE = re.compile(
    r'\[ENT\d\]'           
    r'|\(\d+/\d+\)'        # (3/4) - колонтитул
    r'|[∈∉∅⩽⩾∧∨¬↔]'       # матем. символы
    r'|:='                 
    r'|\(cid:\d+\)',       # артефакт PDF
    re.IGNORECASE,
)


def is_bad_source(source: str) -> bool:
    return bool(BAD_SOURCE.search(source)) or len(source.strip()) < 10


def has_duplicate_options(q: dict) -> bool:
    opts = [o.lower().strip() for o in q.get("options", [])]
    return len(opts) != len(set(opts))


def correct_in_wrong(q: dict) -> bool:
    correct = q.get("correct", "").lower().strip()
    opts    = [o.lower().strip() for o in q.get("options", [])]
    return opts.count(correct) > 1


def check_question(q: dict) -> list[str]:
    """Возвращает список причин удаления
    """
    reasons = []

    correct = q.get("correct", "")
    if is_bad_concept(correct):
        reasons.append(f"кривой concept (correct): «{correct}»")

    for opt in q.get("options", []):
        if opt == correct and is_bad_concept(opt):
            reasons.append(f"кривой concept в ответе: «{opt}»")
            break

    source = q.get("source", "")
    if is_bad_source(source):
        reasons.append(f"мусорный source: «{source[:60]}»")

    if has_duplicate_options(q):
        reasons.append("дубли в options")

    if correct_in_wrong(q):
        reasons.append("correct совпадает с дистрактором")

    return reasons


def deduplicate(questions: list[dict]) -> tuple[list[dict], int]:
    """удаления вопросов с одинаковым текстом вопроса"""
    seen    = set()
    result  = []
    removed = 0
    for q in questions:
        key = q.get("question", "").lower().strip()
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        result.append(q)
    return result, removed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src",    default=str(SRC_PATH))
    parser.add_argument("--out",    default=str(OUT_PATH))
    parser.add_argument("--report", action="store_true",
                        help="Показать что будет удалено, не сохранять")
    args = parser.parse_args()

    questions = json.loads(Path(args.src).read_text(encoding="utf-8"))
    print(f"Загружено вопросов: {len(questions)}")

    #дедупликация
    # questions, n_dedup = deduplicate(questions)
    # print(f"  дубликатов вопросов удалено: {n_dedup}")

    #фильтрация
    good, bad = [], []
    for q in questions:
        reasons = check_question(q)
        if reasons:
            bad.append((q, reasons))
        else:
            good.append(q)

    print(f"  отфильтровано плохих: {len(bad)}")
    print(f"  осталось хороших:     {len(good)}")

    if args.report:
        print(f"\n{'='*60}")
        print("УДАЛЯЕМЫЕ ВОПРОСЫ:")
        for q, reasons in bad:
            print(f"\n  Вопрос: {q['question']}")
            print(f"  Ответ:  {q['correct']}")
            for r in reasons:
                print(f"  ! {r}")
        return

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(good, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nСохранено: {out_path}")


if __name__ == "__main__":
    main()