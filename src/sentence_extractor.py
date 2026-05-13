import argparse
import json
import re
from pathlib import Path

BASE_DIR  = Path(__file__).resolve().parent.parent
TXT_PATH  = BASE_DIR / "data" / "DM2024.txt"
OUT_PATH  = BASE_DIR / "data" / "source_items.json"
MIN_WORDS = 5



MATH_CHARS = re.compile(r'[∈∉∅⩽⩾∀∃∨∧¬→↔∩∪⊆⊂⊃±×÷√∞∑∏⟨⟩≡≠≈∼]')
LATIN_LONG = re.compile(r'[A-Za-z]{5,}')          
FORMULA    = re.compile(r':=|\{[^}]{0,60}\||\(cid:\d+\)|\\[a-zA-Z]+')
PAGENUM    = re.compile(r'^\s*\d+/\d+\s*$')
PAGE_MARK  = re.compile(r'---\s*PAGE\s*\d+\s*---')
DIGITS_LONG = re.compile(r'\d{4,}')

GLUED = re.compile(r'[а-яёА-ЯЁ]{20,}')


def is_bad_line(line: str) -> bool:
    if PAGENUM.match(line):
        return True
    if PAGE_MARK.search(line):
        return True
    if MATH_CHARS.search(line):
        return True
    if FORMULA.search(line):
        return True
    if LATIN_LONG.search(line):
        return True
    if DIGITS_LONG.search(line):
        return True
    if GLUED.search(line):
        return True
    return False


def clean_text(raw: str) -> str:
    lines = raw.splitlines()
    good_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if is_bad_line(line):
            continue
        good_lines.append(line)

    text = ' '.join(good_lines)

    # склеивние дефисных переносов
    text = re.sub(r'([а-яёА-ЯЁa-zA-Z])-\s+([а-яёА-ЯЁa-zA-Z])', r'\1\2', text)

    text = re.sub(r'\s+', ' ', text).strip()
    return text


# Разбивка на предложения
#  точки в аббревиатурах остаются
ABBREVS = re.compile(
    r'\b(т\.е|т\.д|т\.п|и т|рис|стр|см|др|напр|ср|н\.э|ок|гл|разд|п|пп)\.',
    re.IGNORECASE,
)


def split_sentences(text: str) -> list[str]:
    text = ABBREVS.sub(lambda m: m.group().replace('.', '‹DOT›'), text)
    # Режем по [.!?] + пробел + заглавная буква/кавычка
    parts = re.split(r'(?<=[.!?])\s+(?=[А-ЯЁA-Z«"—–])', text)
    result = []
    for p in parts:
        p = p.replace('‹DOT›', '.').strip()
        if p:
            result.append(p)
    return result


def filter_sentence(s: str, min_words: int) -> bool:
    words = s.split()
    if len(words) < min_words:
        return False
    if not re.search(r'[а-яёА-ЯЁ]', s):
        return False
    if not re.match(r'^[А-ЯЁа-яёA-Za-z«"—–]', s):
        return False
    if MATH_CHARS.search(s) or FORMULA.search(s):
        return False
    return True



def parse_page_range(spec: str) -> set[int]:
    pages: set[int] = set()
    for part in spec.split(','):
        part = part.strip()
        if '-' in part:
            a, b = part.split('-', 1)
            pages.update(range(int(a), int(b) + 1))
        else:
            pages.add(int(part))
    return pages


def extract_pages(raw: str, page_range: set[int] | None) -> str:
    if page_range is None:
   
        return re.sub(r'---\s*PAGE\s*\d+\s*---', ' ', raw)

    result: list[str] = []
    current_page: int | None = None
    current_lines: list[str] = []

    for line in raw.splitlines():
        m = re.match(r'---\s*PAGE\s*(\d+)\s*---', line)
        if m:
            if current_page in page_range:
                result.append('\n'.join(current_lines))
            current_page = int(m.group(1))
            current_lines = []
        else:
            current_lines.append(line)

    if current_page in page_range:
        result.append('\n'.join(current_lines))

    return '\n'.join(result)

def main():
    parser = argparse.ArgumentParser(description='TXT → source_items.json')
    parser.add_argument('--txt',       default=str(TXT_PATH))
    parser.add_argument('--out',       default=str(OUT_PATH))
    parser.add_argument('--pages',     default=None,
                        help='Диапазон страниц, напр. 44-300 или 44-120,200-250')
    parser.add_argument('--min-words', type=int, default=MIN_WORDS)
    args = parser.parse_args()

    print(f'Читаем: {args.txt}')
    raw = Path(args.txt).read_text(encoding='utf-8')

    page_range = parse_page_range(args.pages) if args.pages else None
    page_text  = extract_pages(raw, page_range)
    clean      = clean_text(page_text)
    sentences  = split_sentences(clean)
    sentences  = [s for s in sentences if filter_sentence(s, args.min_words)]

    print(f'Предложений после фильтрации: {len(sentences)}')

    items = [
        {'sentence': s, 'concept1': '', 'concept2': '', 'relation': ''}
        for s in sentences
    ]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(f'Сохранено: {out_path}')
    print()
    print('Следующий шаг:')
    print('  python src/auto_annotate.py')


if __name__ == '__main__':
    main()