from app.database import raw_pages_collection, chapters_collection
# from services.toc_extractor import extract_toc
from services.toc_extractor import extract_toc


async def build_chapters(book_id: str):

    # 1️⃣ Get all pages for this book first
    all_pages = await raw_pages_collection.find(
        {"book_id": book_id}
    ).sort("page", 1).to_list(None)

    if not all_pages:
        raise Exception("No pages found for this book")

    last_page = all_pages[-1]["page"]
    results = []

    # 2️⃣ Try to get TOC
    try:
        toc = await extract_toc(book_id)
        if not toc:
            raise Exception("TOC empty")
        
        # 3️⃣ Build chapters from TOC
        for i, chapter in enumerate(toc):
            start = chapter["start_page"]

            end = (
                toc[i + 1]["start_page"]
                if i + 1 < len(toc)
                else last_page + 1
            )

            chapter_pages = [
                p for p in all_pages
                if start <= p["page"] < end
            ]

            full_text = "\n".join(p["text"] for p in chapter_pages)

            doc = {
                "book_id": book_id,
                "chapter_index": chapter["index"],
                "title": chapter["title"],
                "start_page": start,
                "end_page": end - 1,
                "text": full_text,
            }

            await chapters_collection.insert_one(doc)
            results.append(doc)

    except Exception as e:
        print(f"⚠️ TOC extraction failed or not found: {e}. Falling back to single chapter.")
        
        # Fallback: Treat whole book as one chapter
        full_text = "\n".join(p["text"] for p in all_pages)
        
        doc = {
            "book_id": book_id,
            "chapter_index": 1,
            "title": "Full Book Content",
            "start_page": all_pages[0]["page"],
            "end_page": last_page,
            "text": full_text,
        }
        
        await chapters_collection.insert_one(doc)
        results.append(doc)

    return results
