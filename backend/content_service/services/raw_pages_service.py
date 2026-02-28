from app.database import raw_pages_collection

async def get_all_pages(book_id: str):
    cursor = raw_pages_collection.find(
        {"book_id": book_id},
        {"_id": 0}
    ).sort("page", 1)

    return await cursor.to_list(length=None)
