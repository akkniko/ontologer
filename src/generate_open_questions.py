"""
============================================================================================================================
generate_open_questions.py
генерирует открытые вопросы с эталонными ответами из исходного датасета
и фильтрует мусор

Запуск:
    python src/generate_open_questions.py
    python src/generate_open_questions.py --source data/train_dataset.json --out data/open_questions_clean.json
============================================================================================================================
"""

import json
import re
import argparse
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

#шаблоны, по которм составляются открытые вопросы
TEMPLATES = {
    "generalization": [
        # определение
        {"question": "Что такое {concept1}?",                                          "type": "definition"},
        {"question": "Дайте определение понятию «{concept1}».",                        "type": "definition"},
        {"question": "Что понимается под термином «{concept1}» в дискретной математике?", "type": "definition"},
        # отношение
        {"question": "Как {concept1} соотносится с понятием «{concept2}»?",            "type": "relation"},
        {"question": "В чём состоит связь между {concept1} и {concept2}?",             "type": "relation"},
        {"question": "Как {concept1} связано с {concept2}?",                           "type": "relation"},
        # частный случай
        {"question": "Является ли {concept1} частным случаем {concept2}? Объясните.", "type": "is_a"},
        {"question": "Почему {concept1} считается разновидностью {concept2}?",         "type": "is_a"},
        # сравнение
        {"question": "Чем {concept1} отличается от {concept2} и что у них общего?",   "type": "compare"},
        {"question": "Сравните понятия {concept1} и {concept2}.",                      "type": "compare"},
    ],
    "aggregation": [
        # состав
        {"question": "Из чего состоит {concept2}? Какую роль играет {concept1}?",      "type": "composition"},
        {"question": "Как {concept1} входит в состав {concept2}?",                      "type": "part_of"},
        {"question": "Что является элементом {concept2}?",                              "type": "composition"},
        {"question": "Какова структура {concept2} с точки зрения {concept1}?",          "type": "structure"},
        # отношение
        {"question": "Опишите связь между {concept1} и {concept2}.",                    "type": "relation"},
        {"question": "Как соотносятся {concept1} и {concept2}?",                        "type": "relation"},
    ],
    "composition": [
        {"question": "Что такое {concept2} и как оно строится из {concept1}?",          "type": "definition"},
        {"question": "Как {concept1} используется при построении {concept2}?",          "type": "composition"},
        {"question": "Опишите связь между {concept1} и {concept2}.",                    "type": "relation"},
        {"question": "Какова роль {concept1} в определении {concept2}?",                "type": "role"},
        {"question": "Объясните, как {concept1} и {concept2} связаны между собой.",     "type": "explain"},
    ],
    "association": [
        {"question": "Как связаны понятия «{concept1}» и «{concept2}»?",               "type": "relation"},
        {"question": "Какова роль {concept1} по отношению к {concept2}?",              "type": "role"},
        {"question": "Объясните взаимосвязь между {concept1} и {concept2}.",           "type": "explain"},
        {"question": "Что общего между {concept1} и {concept2}?",                      "type": "compare"},
        {"question": "Каким образом {concept1} используется вместе с {concept2}?",     "type": "usage"},
        {"question": "В чём заключается связь {concept1} с {concept2}?",               "type": "relation"},
    ],
    "default": [
        {"question": "Объясните связь между понятиями «{concept1}» и «{concept2}».",   "type": "relation"},
        {"question": "Что общего между {concept1} и {concept2}?",                      "type": "compare"},
        {"question": "Как соотносятся {concept1} и {concept2}?",                       "type": "relation"},
    ],
}

TRASH_PATTERNS = [
    r"^\s*\(.*\)\s*$",
    r"(?i)^\s*теорема\s+о\s+[а-яё\s\-]+(?:\.|\s*)$",
    r"(?i)^[а-яё\s\,]+теорема\s+о\s+[а-яё\s]+(?:\.|\s*)$",
    r"(?i)^\s*(?:теорема|следствие|определение)\s*\.?\s*$",
    r"(?i)^\s*(?:глава|раздел|параграф)\s+\d+.*$",
    r"[a-zA-Z]{3,}\d",        
    r"\d[a-zA-Z]{2,}",
    r"\[\s*,\s*,",            
]

GOOD_MARKERS = [
    r"—\s*это", r"называется", r"является", r"состоит из",
    r"содержит", r"включает", r"отображает", r"сохраняет",
    r"связывает", r"обобщение", r"частный случай",
]


def build_reference_answer(item: dict) -> str:
    text = item.get("text") or item.get("sentence") or ""
    c1   = item.get("concept1", "")
    c2   = item.get("concept2", "")
    text = text.replace("[ENT1]", c1).replace("[ENT2]", c2)
    return " ".join(text.split())


def is_trash(text: str) -> bool:
    if not text or len(text.strip()) < 6:
        return True
    for pat in TRASH_PATTERNS:
        if re.search(pat, text):
            return True
    return False


def quality_score(text: str) -> int:
    score = 0
    length = len(text)
    if 30 <= length <= 250:
        score += 3
    elif length > 250:
        score += 1
    for pat in GOOD_MARKERS:
        if re.search(pat, text, re.IGNORECASE):
            score += 2
    return score


def best_reference(candidates: list) -> str:
    good = [t for t in candidates if not is_trash(t)]
    if not good:
        return max(candidates, key=len) if candidates else ""
    return max(good, key=quality_score)


def generate_questions(items: list, seed: int = 42, count: int = None) -> list:
    random.seed(seed)
    groups: dict = {}
    meta:   dict = {}

    for item in items:
        c1    = item.get("concept1", "").strip()
        c2    = item.get("concept2", "").strip()
        label = item.get("label") or item.get("relation") or "default"

        if not c1 or not c2:
            continue

        reference = build_reference_answer(item)
        if not reference:
            continue

        templates = TEMPLATES.get(label, TEMPLATES["default"])

        for tmpl in templates:
            question_text = tmpl["question"].format(concept1=c1, concept2=c2)
            key = (question_text, c1, c2)

            if key not in groups:
                groups[key] = []
                meta[key]   = {
                    "question":      question_text,
                    "concept1":      c1,
                    "concept2":      c2,
                    "relation":      label,
                    "question_type": tmpl["type"],
                }
            groups[key].append(reference)

    result      = []
    skipped     = 0

    for key, refs in groups.items():
        chosen = best_reference(refs)
        if is_trash(chosen):
            skipped += 1
            continue
        entry = dict(meta[key])
        entry["reference_answer"] = chosen
        result.append(entry)

    print(f"Уникальных пар вопрос-концепты: {len(groups)}")
    print(f"Удалено:                 {skipped}")
    print(f"Оставлено валидных вопросов:    {len(result)}")

    random.shuffle(result)
    if count:
        result = result[:count]
    return result


def load_items(path: str) -> list:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Ожидался список JSON-объектов, получено: {type(data)}")
    return data


def main():
    parser = argparse.ArgumentParser(description="Генератор открытых вопросов с развёрнутым ответом")
    parser.add_argument("--source", default=str(BASE_DIR / "data" / "train_dataset.json"))
    parser.add_argument("--out",    default=str(BASE_DIR / "data" / "open_questions_clean.json"))
    parser.add_argument("--count",  type=int, default=None, help="Ограничить количество вопросов")
    parser.add_argument("--seed",   type=int, default=123)
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"Входной файл не найден: {source_path}")
        return

    print(f"Загрузка данных из: {source_path}")
    items = load_items(str(source_path))
    print(f"Записей в исходном файле: {len(items)}")

    questions = generate_questions(items, seed=args.seed, count=args.count)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"Сохранено: {out_path}")


if __name__ == "__main__":
    main()