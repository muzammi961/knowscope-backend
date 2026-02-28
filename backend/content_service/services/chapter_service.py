import re
from app.database import chapters_collection

CHAPTER_REGEX = r"CHAPTER\s+(\d+)\s+(.+)"

async def extract_chapters(pages, book_id):
    chapters = []

    for page in pages:
        match = re.search(CHAPTER_REGEX, page["text"], re.IGNORECASE)
        if match:
            chapters.append({
                "book_id": book_id,
                "chapter_number": int(match.group(1)),
                "chapter_name": match.group(2).strip(),
                "start_page": page["page"]
            })

    # set end_page
    for i in range(len(chapters) - 1):
        chapters[i]["end_page"] = chapters[i + 1]["start_page"] - 1

    chapters[-1]["end_page"] = pages[-1]["page"]

    await chapters_collection.insert_many(chapters)
    return chapters
