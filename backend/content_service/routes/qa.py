from fastapi import APIRouter, HTTPException,Depends,Header
from pydantic import BaseModel, Field
from typing import Optional, List
from .jwt_utils import decode_access_token 
from typing import List
from datetime import datetime,timezone
from app.schemas import QuestionRequest, MessageResponse, ConversationResponse, ConversationSummaryResponse ,CreateConversationRequest
from services.qa_service import create_user_if_not_exists, get_or_create_conversation, save_message
from app.database import conversations_collection, messages_collection
from services.qa_service import get_user_conversations,get_conversation_messages
from bson import ObjectId



router = APIRouter(prefix="/api/a", tags=["Question Answering"])

async def get_current_user_from_header(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")
    token = authorization.split(" ")[1]
    try:
        return decode_access_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    



# class QuestionRequest(BaseModel):
#     """
#     Students provide ONLY a question.
#     The system automatically searches all stored textbooks.
#     """
#     question: str = Field(
#         ...,
#         min_length=3,
#         max_length=500,
#         description="The student's question (no class or subject needed)"
#     )
#     top_k: Optional[int] = Field(
#         5, ge=1, le=20,
#         description="Number of textbook chunks to retrieve"
#     )


class QuestionResponse(BaseModel):
    answer: str
    sources: List[dict]
    confidence: float
    total_chunks_used: int


class SearchResponse(BaseModel):
    question: str
    chunks: List[dict]
    total_found: int




router = APIRouter(prefix="/api/qa", tags=["QA"])

# Dummy auth dependency (replace with your JWT auth)
# async def get_current_user_from_header():
#     # Example hardcoded user, replace with JWT decoding
#     return {"user_id": "user123", "email": "user@example.com"}

# # --------------------------
# Ask question endpoint
# --------------------------


@router.get("/me")
async def read_my_profile(current_user: dict = Depends(get_current_user_from_header)):
    # current_user = {'user_id': ..., 'email': ...}
    return {"message": "Current user fetched successfully", "user": current_user}





@router.post("/ask", response_model=MessageResponse)
async def ask_question(request: QuestionRequest, current_user: dict = Depends(get_current_user_from_header)):
    from services.rag_graph import rag_graph  # Your LangGraph pipeline

    user_id = current_user["user_id"]
    email = current_user.get("email", "")
    
    await create_user_if_not_exists(user_id, email)
    conversation = await get_or_create_conversation(user_id=user_id,conversation_id=request.conversation_id,title=request.conversation_title) 
    result = await rag_graph.ainvoke({
        "question": request.question,
        "top_k": request.top_k,
        "embedding": [],
        "chunks": [],
        "answer": "",
        "sources": [],
        "confidence": 0.0
    })

    # 4️⃣ Low confidence guard
    if result["confidence"] < 0.25 and len(result["chunks"]) < 2:
        result["answer"] = "No answer found in textbook."

    # 5️⃣ Save message in MongoDB
    saved_msg = await save_message(
        conversation_id=str(conversation["_id"]),
        question=request.question,
        answer=result["answer"],
        sources=result["sources"],
        confidence=result["confidence"]
    )

    return MessageResponse(
        question=saved_msg["question"],
        answer=saved_msg["answer"],
        sources=saved_msg["sources"],
        confidence=saved_msg["confidence"],
        created_at=saved_msg["created_at"]
    )
    
    
    

# --------------------------
# Get all conversations for user
# --------------------------
@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(current_user: dict = Depends(get_current_user_from_header)):
    user_id = current_user["user_id"]
    
    conv_cursor = conversations_collection.find({"user_id": user_id})
    conv_list = []
    async for conv in conv_cursor:
        messages_cursor = messages_collection.find({"conversation_id": conv["_id"]})
        msgs = []
        async for m in messages_cursor:
            msgs.append(MessageResponse(
                question=m["question"],
                answer=m["answer"],
                sources=m["sources"],
                confidence=m["confidence"],
                created_at=m["created_at"]
            ))
        conv_list.append(ConversationResponse(
            conversation_id=str(conv["_id"]),
            title=conv["title"],
            messages=msgs
        ))
    return conv_list





@router.post("/create_new_conversation", response_model=ConversationSummaryResponse)
async def create_conversation(payload: CreateConversationRequest,current_user: dict = Depends(get_current_user_from_header)):
    user_id = str(current_user.get("user_id"))
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user")
    conversation_data = {"user_id": user_id, "title": payload.title or "New Conversation","created_at": datetime.now(timezone.utc)}
    result = await conversations_collection.insert_one(conversation_data)
    return {"conversation_id": str(result.inserted_id),"title": conversation_data["title"],"created_at": conversation_data["created_at"]}





@router.get("/one_by_one_conversation", response_model=List[ConversationSummaryResponse])
async def list_conversations(current_user: dict = Depends(get_current_user_from_header)):
    user_id = str(current_user.get("user_id"))
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user")    
    conv_list = await get_user_conversations(user_id)
    return conv_list



# 2️⃣ Get all messages by conversation_id
@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def list_conversation_messages(conversation_id: str, current_user: dict = Depends(get_current_user_from_header)):
    user_id = current_user["user_id"]
    msgs = await get_conversation_messages(user_id, conversation_id)
    if msgs is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return msgs


@router.delete("/{conversation_id}/conversation_delete_onebyone", status_code=200)
async def delete_conversation(conversation_id: str,current_user: dict = Depends(get_current_user_from_header)):
    user_id = str(current_user.get("user_id"))
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user")
    try:
        conv_object_id = ObjectId(conversation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")
    conversation = await conversations_collection.find_one({"_id": conv_object_id,"user_id": user_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await conversations_collection.delete_one({"_id": conv_object_id})
    await messages_collection.delete_many({"conversation_id": conv_object_id})
    return {"message": "Conversation deleted successfully"}






@router.put("/{conversation_id}/update_conversation_title", response_model=ConversationSummaryResponse)
async def update_conversation_title(conversation_id: str,payload: CreateConversationRequest,current_user: dict = Depends(get_current_user_from_header)):
    user_id = str(current_user.get("user_id"))
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user")
    result = await conversations_collection.update_one({"_id": ObjectId(conversation_id),"user_id": user_id},{"$set": {"title": payload.title}})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    updated_conversation = await conversations_collection.find_one({"_id": ObjectId(conversation_id)})
    return {"conversation_id": str(updated_conversation["_id"]),"title": updated_conversation["title"],"created_at": updated_conversation["created_at"]}







# ─────────────────────────────────────────────
# POST /api/qa/search  — Context-only (no LLM)
# ─────────────────────────────────────────────

@router.post("/search", response_model=SearchResponse)
async def search_chunks(request: QuestionRequest):
    """
    Return raw textbook chunks for a question without calling any LLM.
    Useful for debugging, verifying vector search quality, or free-tier use.
    """
    try:
        from services.embedding_service import generate_embedding
        from app.vector_store import vector_store

        embedding = await generate_embedding(request.question)
        chunks = await vector_store.search_similar(
            query_embedding=embedding,
            top_k=request.top_k
        )

        return SearchResponse(
            question=request.question,
            chunks=chunks,
            total_found=len(chunks)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# GET /api/qa/stats  — Vector store statistics
# ─────────────────────────────────────────────

@router.get("/stats")
async def get_vector_store_stats():
    """Get statistics about the ChromaDB vector store."""
    try:
        from app.vector_store import vector_store
        stats = await vector_store.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# GET /api/qa/books  — List indexed books
# ─────────────────────────────────────────────

@router.get("/books")
async def list_indexed_books():
    """
    List all book IDs that have chunks stored in the ChromaDB vector store.
    Useful to confirm which textbooks are available for Q&A.
    """
    try:
        from app.vector_store import collection

        # Peek at all stored metadata to find unique book_ids
        # ChromaDB doesn't have a distinct() query, so we retrieve all metadata
        total = collection.count()
        if total == 0:
            return {"total_books": 0, "books": [], "total_chunks": 0}

        # Get all metadata (up to 10000 entries)
        results = collection.get(include=["metadatas"], limit=min(total, 10000))
        book_ids = list({
            meta["book_id"]
            for meta in results["metadatas"]
            if "book_id" in meta
        })

        return {
            "total_books": len(book_ids),
            "books": sorted(book_ids),
            "total_chunks": total
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# DELETE /api/qa/book/{book_id}
# ─────────────────────────────────────────────

@router.delete("/book/{book_id}")
async def delete_book_chunks(book_id: str):
    """Delete all vector chunks for a specific book from ChromaDB."""
    try:
        from app.vector_store import vector_store
        success = await vector_store.delete_book_chunks(book_id)
        if success:
            return {"message": f"✅ Deleted all vector chunks for book: {book_id}"}
        else:
            return {"message": f"❌ Failed to delete chunks for book: {book_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
    
    