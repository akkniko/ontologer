import argparse
import io
import json
import random
import sys
from pathlib import Path

# Фикс кодировки для винды(можно в целом и убрать)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR       = Path(__file__).resolve().parent.parent
RELATIONS_PATH = BASE_DIR / "data" / "source_items_annotated.json"  
DISTRACTORS    = 3


REL_GENITIVE = {
    "наследование": "наследования",
    "агрегация":    "агрегации",
    "ассоциация":   "ассоциации",
}


def _distract(correct: str, exclude: str, pool: list[str]) -> list[str]:
    candidates = [c for c in pool if c != correct and c != exclude]
    random.shuffle(candidates)
    return candidates[:DISTRACTORS]


def _make_options(correct: str, distractors: list[str]) -> list[str]:
    opts = [correct] + distractors
    random.shuffle(opts)
    return opts


def _q(question, correct, distractors, sentence, qtype) -> dict | None:
    if len(distractors) < DISTRACTORS:
        return None
    return {
        "question": question,
        "options":  _make_options(correct, distractors),
        "correct":  correct,
        "source":   sentence,
        "type":     qtype,
    }


# 5 типов вопросов 

"""Какое понятие связано с «C1» отношением X? → C2"""
def q1_related_to_c1(r, pool):
    rel = REL_GENITIVE.get(r["relation"], r["relation"])
    return _q(
        question    = f'Какое понятие связано с понятием «{r["concept1"]}» отношением {rel}?',
        correct     = r["concept2"],
        distractors = _distract(r["concept2"], r["concept1"], pool),
        sentence    = r["sentence"],
        qtype       = "related_to_c1",
    )


    """Какое понятие связано с «C2» отношением X? → C1"""
def q2_related_to_c2(r, pool):
    rel = REL_GENITIVE.get(r["relation"], r["relation"])
    return _q(
        question    = f'Какое понятие связано с понятием «{r["concept2"]}» отношением {rel}?',
        correct     = r["concept1"],
        distractors = _distract(r["concept1"], r["concept2"], pool),
        sentence    = r["sentence"],
        qtype       = "related_to_c2",
    )


    """Каким отношением связаны «C1» и «C2»? → relation"""
def q3_what_relation(r, pool):
    all_rels   = list(REL_GENITIVE.values())
    wrong_rels = [rel for rel in all_rels if rel != REL_GENITIVE[r["relation"]]]
    correct    = REL_GENITIVE[r["relation"]]
    opts       = [correct] + wrong_rels
    random.shuffle(opts)
    return {
        "question": f'Каким отношением связаны понятия «{r["concept1"]}» и «{r["concept2"]}»?',
        "options":  opts,
        "correct":  correct,
        "source":   r["sentence"],
        "type":     "what_relation",
    }


    """ Что является частным случаем «C2»? → C1"""
def q4_subtype_of(r, pool):
    if r["relation"] != "наследование":
        return None
    return _q(
        question    = f'Что является частным случаем понятия «{r["concept2"]}»?',
        correct     = r["concept1"],
        distractors = _distract(r["concept1"], r["concept2"], pool),
        sentence    = r["sentence"],
        qtype       = "subtype_of",
    )


    """Из чего состоит / что включает «C1»? → C2"""
def q5_consists_of(r, pool):
    if r["relation"] != "агрегация":
        return None
    return _q(
        question    = f'Из чего состоит (что включает в себя) понятие «{r["concept1"]}»?',
        correct     = r["concept2"],
        distractors = _distract(r["concept2"], r["concept1"], pool),
        sentence    = r["sentence"],
        qtype       = "consists_of",
    )


GENERATORS = [q1_related_to_c1, q2_related_to_c2, q3_what_relation,
              q4_subtype_of,    q5_consists_of]



"""Загрузка только размеченных записей (с заполненными полями)"""
def load_records(path: Path) -> list[dict]:
    raw      = json.loads(path.read_text(encoding="utf-8"))
    complete = [
        r for r in raw
        if r.get("concept1") and r.get("concept2") and r.get("relation")
    ]
    return complete


def build_concept_pool(records: list[dict]) -> list[str]:
    pool = set()
    for r in records:
        pool.add(r["concept1"])
        pool.add(r["concept2"])
    return list(pool)


def generate_all(records: list[dict]) -> list[dict]:
    pool      = build_concept_pool(records)
    questions = []
    for r in records:
        for gen in GENERATORS:
            q = gen(r, pool)
            if q:
                questions.append(q)
    return questions


def print_questions(questions: list[dict]) -> None:
    for i, q in enumerate(questions, 1):
        print(f"\n{'─'*60}")
        print(f"Вопрос {i} [{q['type']}]")
        print(f"  {q['question']}")
        for j, opt in enumerate(q["options"], 1):
            mark = "+" if opt == q["correct"] else " "
            print(f"  {mark} {j}. {opt}")
        print(f"   Источник: {q['source']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(RELATIONS_PATH))
    parser.add_argument("--out",    default=str(BASE_DIR / "data" / "questions.json"),
                        help="Сохранить вопросы в JSON (default: data/questions.json)")
    parser.add_argument("--count",  type=int, default=None,
                        help="Ограничить количество вопросов")
    parser.add_argument("--seed",   type=int, default=42)
    parser.add_argument("--print",  dest="print_console", action="store_true",
                        help="Также вывести вопросы в консоль")
    args = parser.parse_args()

    random.seed(args.seed)

    src_path = Path(args.source)
    if not src_path.exists():
        print(f"Файл не найден: {src_path}")
        print("Сначала запустите sentence_extractor.py и заполните разметку.")
        return

    records = load_records(src_path)
    if not records:
        print("Нет размеченных записей")
        return

    print(f"Размеченных троек: {len(records)}")
    pool = build_concept_pool(records)
    print(f"Уникальных понятий: {len(pool)}")

    questions = generate_all(records)

    if args.count:
        random.shuffle(questions)
        questions = questions[:args.count]

    print(f"Сгенерировано вопросов: {len(questions)}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(questions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Сохранено: {out_path}")
    
    if getattr(args, 'print_console', False):
        print_questions(questions)


if __name__ == "__main__":
    main()