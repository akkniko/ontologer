from pathlib import Path
import pdfplumber


def extract_pdf_text(pdf_path: Path) -> str:
    parts = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text:
                parts.append(f"\n--- PAGE {i} ---\n")
                parts.append(text)

    return "\n".join(parts)


def main():
    base_dir = Path(__file__).resolve().parent.parent
    pdf_path = base_dir / "data" / "DM2024.pdf"
    out_path = base_dir / "data" / "DM2024.txt"

    print("Start")
    text = extract_pdf_text(pdf_path)
    out_path.write_text(text, encoding="utf-8")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()