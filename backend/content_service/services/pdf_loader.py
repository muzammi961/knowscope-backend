import pdfplumber
from utils.text_cleaner import normalize_text

def extract_pages(pdf_path: str):
    pages = []

    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages):
            raw_text = page.extract_text()
            if raw_text and len(raw_text.strip()) > 30:
                # Clean text: remove headers/footers, artifacts, normalize whitespace
                cleaned = normalize_text(raw_text)
                if cleaned:
                    pages.append({
                        "page": idx + 1,
                        "text": cleaned
                    })

    return pages
