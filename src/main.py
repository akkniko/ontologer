'''
==========================================================================================
менй нужен для извлечения из учебника пдф текстовые данные
сначала использовал pdfplumber - тот плохо извлекал текст
попробовал pymupdf - результат стал гораздо лучше, но версию питона тогда нужно
использовать до 3.13, либо иметь на компе visual studio code c\c++ с устновленным sdk 
(у меня такого не было, поэтому использовал питон 3.12.7)
==========================================================================================
'''

from pathlib import Path
import re



''' 
#с fitz возникли пробелмы на винде, но на линуксе у меня он нормально работает
try:
    import fitz
    BACKEND = "pymupdf"
except ImportError:
    fitz = None
    BACKEND = None
'''

# Резерв: pdfminer.six
from pdfminer.high_level import extract_text as pdfminer_extract
BACKEND = "pdfminer"


def extract_with_pymupdf(pdf_path: Path) -> str:
    doc = fitz.open(str(pdf_path))
    parts = []

    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("blocks")

        blocks.sort(key=lambda b: (round(b[1] / 20), b[0]))

        page_lines = []
        for block in blocks:
            if block[6] != 0:   # 0 - текстовый блок а 1 - картинка
                continue
            text = block[4].strip()
            if not text:
                continue
            # склеивание переноса слов через дефис внутри блока
            text = re.sub(r'([а-яёА-ЯЁa-zA-Z])-\n([а-яёА-ЯЁa-zA-Z])', r'\1\2', text)
            text = text.replace('\n', ' ')
            text = re.sub(r'\s+', ' ', text).strip() #normализация пробелов
            if text:
                page_lines.append(text)

        if page_lines:
            parts.append(f"\n--- PAGE {page_num} ---\n")
            parts.append('\n'.join(page_lines))

    doc.close()
    return '\n'.join(parts)


'''
        ⭡
2 варианта извлечения текста - с pdfminer если pymupdf не работает или 
выдает ошибки(например проблемы с fitz)
        ⭣
'''

def extract_with_pdfminer(pdf_path: Path) -> str:
    from pdfminer.high_level import extract_text
    from io import StringIO

    parts = []
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextContainer
        for page_num, page_layout in enumerate(extract_pages(str(pdf_path)), start=1):
            lines = []
            for element in page_layout:
                if isinstance(element, LTTextContainer):
                    text = element.get_text().strip()
                    text = re.sub(r'([а-яёА-ЯЁa-zA-Z])-\n([а-яёА-ЯЁa-zA-Z])',
                                  r'\1\2', text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    if text:
                        lines.append(text)
            if lines:
                parts.append(f"\n--- PAGE {page_num} ---\n")
                parts.append('\n'.join(lines))
    except Exception:
        text = extract_text(str(pdf_path))
        parts.append(text)

    return '\n'.join(parts)


def extract_pdf_text(pdf_path: Path) -> str:
    if BACKEND == "pymupdf":
        print("Backend: PyMuPDF")
        return extract_with_pymupdf(pdf_path)
    elif BACKEND == "pdfminer":
        print("Backend: pdfminer.six")
        return extract_with_pdfminer(pdf_path)
    else:
        raise ImportError(
            "Neither pymupdf nor pdfminer.six is installed.\n"
            "Install one of them:\n"
            "  pip install pymupdf==1.23.8\n"
            "  pip install pdfminer.six"
        )



def main():
    base_dir = Path(__file__).resolve().parent.parent
    pdf_path = base_dir / "data" / "DM2024.pdf"
    out_path = base_dir / "data" / "DM2024.txt"

    print("Start")
    print(f"PDF: {pdf_path}")

    text = extract_pdf_text(pdf_path)

    out_path.write_text(text, encoding="utf-8")
    print(f"Saved: {out_path}")

    pages = text.count("--- PAGE ")
    chars = len(text)
    print(f"Pages: {pages}, characters: {chars:,}")


if __name__ == "__main__":
    main()