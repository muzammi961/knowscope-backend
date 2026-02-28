import asyncio
import sys
# from services.chapter_pipeline import build_chapters
from services.chapter_pipeline import build_chapters

async def main(book_id: str):
    chapters = await build_chapters(book_id)
    print(f"Inserted {len(chapters)} chapters")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_chapter_pipeline.py <book_id>")
        sys.exit(1)

    book_id = sys.argv[1]
    asyncio.run(main(book_id))
