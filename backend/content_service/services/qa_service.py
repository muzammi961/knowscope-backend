from app.database import users_collection, conversations_collection, messages_collection
from datetime import datetime
from bson import ObjectId
from fastapi import  HTTPException


async def create_user_if_not_exists(user_id: str, email: str):
    user = await users_collection.find_one({"user_id": user_id})
    if not user:
        await users_collection.insert_one({
            "user_id": user_id,
            "email": email,
            "created_at": datetime.utcnow()
        })
    return user_id

# async def get_or_create_conversation(user_id: str, title: str):
#     conv = await conversations_collection.find_one({"user_id": user_id, "title": title})
#     if not conv:
#         conv_doc = {"user_id": user_id, "title": title, "created_at": datetime.utcnow()}
#         result = await conversations_collection.insert_one(conv_doc)
#         conv = await conversations_collection.find_one({"_id": result.inserted_id})
#     return conv

async def get_or_create_conversation(user_id: str,conversation_id: str | None,title: str | None):
    if conversation_id:
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(status_code=400, detail="Invalid conversation_id")
        conv = await conversations_collection.find_one({"_id": ObjectId(conversation_id),"user_id": user_id})
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conv
    conv_doc = {"user_id": user_id,"title": title or "New Conversation","created_at": datetime.utcnow()}
    result = await conversations_collection.insert_one(conv_doc)
    return await conversations_collection.find_one({"_id": result.inserted_id})




async def save_message(conversation_id: str, question: str, answer: str, sources: list, confidence: float):
    msg = {
        "conversation_id": ObjectId(conversation_id),
        "question": question,
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "created_at": datetime.utcnow()
    }
    result = await messages_collection.insert_one(msg)
    return await messages_collection.find_one({"_id": result.inserted_id})








async def get_user_conversations(user_id: str):
    conv_cursor = conversations_collection.find({"user_id": user_id}).sort("created_at", -1)
    conv_list = []
    async for conv in conv_cursor:
        conv_list.append({"conversation_id": str(conv["_id"]),"title": conv.get("title", ""),"created_at": conv.get("created_at", datetime.utcnow())})
    return conv_list







# Get all messages in a conversation
async def get_conversation_messages(user_id: str, conversation_id: str):
    conv = await conversations_collection.find_one({"_id": ObjectId(conversation_id),"user_id": user_id})
    if not conv:
        return None

    messages_cursor = messages_collection.find({"conversation_id": ObjectId(conversation_id)})
    msgs = []
    async for m in messages_cursor:
        msgs.append({"question": m["question"],"answer": m["answer"],"sources": m["sources"],"confidence": m["confidence"],"created_at": m["created_at"]})
    return msgs