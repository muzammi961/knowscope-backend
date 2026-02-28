from app.database import db
from app.models import user_document
from bson import ObjectId

users_collection = db["users"]

async def get_user_by_google_id(google_id: str):
    return await users_collection.find_one({"google_id": google_id})

async def create_user(user_data: dict):
    result = await users_collection.insert_one(user_document(user_data))
    return await users_collection.find_one({"_id": result.inserted_id})

def serialize_user(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user.get("name"),
        "picture": user.get("picture")
    } 