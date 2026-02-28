import asyncio
import sys
from services.topic_extractor import build_topics

async def main(book_id: str):
    await build_topics(book_id)
    print("Topics inserted")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_topic_pipeline.py <book_id>")
        sys.exit(1)

    book_id = sys.argv[1]
    asyncio.run(main(book_id))
