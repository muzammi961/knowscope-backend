# import asyncio
# import sys
# from services.chunk_builder import build_chunks


# async def main(book_id: str):
#     await build_chunks(book_id)
#     print("Chunks created")

# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage: python run_chunk_pipeline.py <book_id>")
#         sys.exit(1)

#     book_id = sys.argv[1]
#     asyncio.run(main(book_id))



import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.chunk_builder import build_chunks

async def main(book_id: str, class_number: int, subject: str):
    chunks_created = await build_chunks(book_id, class_number, subject)
    print(f"✅ Created {chunks_created} chunks and added to ChromaDB")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python run_chunk_pipeline.py <book_id> <class> <subject>")
        print("Example: python run_chunk_pipeline.py physics_10 10 physics")
        sys.exit(1)

    book_id = sys.argv[1]
    class_number = int(sys.argv[2])
    subject = sys.argv[3]
    
    asyncio.run(main(book_id, class_number, subject))