import re
from app.database import raw_pages_collection

TOC_LINE_REGEX = re.compile(
    r"^\s*(\d+)\s+(.+?)\s*[-–—]+\s*(\d+)\s*$",
    re.MULTILINE
)

async def extract_toc(book_id: str):
    toc_page = await raw_pages_collection.find_one({
        "book_id": book_id,
        "text": {"$regex": "Contents", "$options": "i"}
    })

    if not toc_page:
        raise RuntimeError("TOC page not found")

    matches = TOC_LINE_REGEX.findall(toc_page["text"])
    print("TOC MATCHES:", matches) 

    if not matches:
        raise RuntimeError("TOC parsing failed")

    chapters = []
    for idx, title, page in matches:
        chapters.append({
            "index": int(idx),
            "title": title.strip(),
            "start_page": int(page),
            "book_id": book_id
        })

    return chapters
