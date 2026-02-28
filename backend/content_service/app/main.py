"""
app/main.py
===========
FastAPI application entry point for the Knowscope Content Service.

Run from the `content_service/` directory:
    uvicorn app.main:app --reload --port 8001
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.ingest import router as ingest_router
from routes.qa import router as qa_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Startup
    from app.vector_store import vector_store
    stats = await vector_store.get_stats()
    print("=" * 50)
    print("  🚀 Knowscope Content Service started")
    print(f"  📦 ChromaDB total chunks: {stats.get('total_chunks', 0)}")
    print("=" * 50)
    yield
    # Shutdown (nothing to clean up for ChromaDB persistent client)
    print("🛑 Knowscope Content Service shutting down")


app = FastAPI(
    title="Knowscope Content Service",
    description=(
        "AI-powered textbook Q&A system using RAG. "
        "Teachers upload PDF textbooks; students ask questions and receive "
        "accurate exam-style answers automatically retrieved from the textbook."
    ),
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware — restrict origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingest_router)
app.include_router(qa_router)


@app.get("/", tags=["Health"])
async def root():
    """Service status and ChromaDB statistics."""
    from app.vector_store import vector_store
    stats = await vector_store.get_stats()
    return {
        "status": "✅ Content Service Running",
        "version": "2.0.0",
        "vector_db": "ChromaDB",
        "vector_db_stats": stats,
        "endpoints": {
            "ingest_pdf":    "POST /ingest/pdf",
            "list_books":    "GET  /ingest/books  |  GET /api/qa/books",
            "delete_book":   "DELETE /ingest/book/{book_id}",
            "ask_question":  "POST /api/qa/ask",
            "search_chunks": "POST /api/qa/search",
            "vector_stats":  "GET  /api/qa/stats",
            "api_docs":      "GET  /docs"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}