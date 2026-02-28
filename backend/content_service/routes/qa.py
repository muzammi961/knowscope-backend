"""
routes/qa.py
============
Student Question-Answering endpoints.

Students provide ONLY a question. The system:
1. Embeds the question using SentenceTransformers.
2. Searches ALL stored textbooks in ChromaDB (no class/subject filter).
3. Generates an exam-style answer via GPT (or returns raw chunks if no API key).

Endpoints:
  POST /api/qa/ask       — Full RAG pipeline (vector search + LLM)
  POST /api/qa/search    — Context-only (vector search, no LLM)
  GET  /api/qa/stats     — ChromaDB vector store statistics
  GET  /api/qa/books     — List all distinct book IDs in the vector store
  DELETE /api/qa/book/{id} — Delete all vector chunks for a specific book
"""

from fastapi import APIRouter, HTTPException,Depends,Header
from pydantic import BaseModel, Field
from typing import Optional, List
from .jwt_utils import decode_access_token 

router = APIRouter(prefix="/api/qa", tags=["Question Answering"])









async def get_current_user_from_header(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")
    token = authorization.split(" ")[1]
    try:
        return decode_access_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    

@router.get("/me")
async def read_my_profile(current_user: dict = Depends(get_current_user_from_header)):
    # current_user = {'user_id': ..., 'email': ...}
    return {"message": "Current user fetched successfully", "user": current_user}









# ─────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────

class QuestionRequest(BaseModel):
    """
    Students provide ONLY a question.
    The system automatically searches all stored textbooks.
    """
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="The student's question (no class or subject needed)"
    )
    top_k: Optional[int] = Field(
        5, ge=1, le=20,
        description="Number of textbook chunks to retrieve"
    )


class QuestionResponse(BaseModel):
    answer: str
    sources: List[dict]
    confidence: float
    total_chunks_used: int


class SearchResponse(BaseModel):
    question: str
    chunks: List[dict]
    total_found: int


# ─────────────────────────────────────────────
# POST /api/qa/ask  — Full RAG (vector search + LLM)
# ─────────────────────────────────────────────

@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Answer a student question using the LangGraph RAG pipeline.
    Automatically searches ALL stored textbooks — no class or subject required.
    """
    try:
        from services.rag_graph import rag_graph

        print(f"📝 Question: {request.question}")

        # Run the LangGraph RAG pipeline
        result = await rag_graph.ainvoke({
            "question": request.question,
            "top_k": request.top_k,
            "embedding": [],
            "chunks": [],
            "answer": "",
            "sources": [],
            "confidence": 0.0
        })

        # Low-confidence guard: if confidence is very low, say so
        answer = result["answer"]
        if result["confidence"] < 0.25 and len(result["chunks"]) < 2:
            answer = "No answer found in textbook."

        return QuestionResponse(
            answer=answer,
            sources=result["sources"],
            confidence=result["confidence"],
            total_chunks_used=len(result["chunks"])
        )

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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