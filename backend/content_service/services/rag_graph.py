"""
LangGraph RAG Pipeline
======================
Graph: embed_question → retrieve_chunks → generate_answer → END

Students provide ONLY a question. The graph automatically:
 1. Embeds the question using the same SentenceTransformer model.
 2. Searches ALL textbooks in ChromaDB (no class/subject filter).
 3. Generates an exam-style answer via GPT (or returns raw chunks if no API key).
"""

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from services.embedding_service import generate_embedding
from app.vector_store import vector_store
from services.gpt_service import gpt_service


# ─────────────────────────────────────────────
# State definition
# ─────────────────────────────────────────────

class RAGState(TypedDict):
    question: str
    top_k: int
    embedding: List[float]
    chunks: List[Dict[str, Any]]
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float


# ─────────────────────────────────────────────
# Node 1: Embed the student's question
# ─────────────────────────────────────────────

async def embed_question(state: RAGState) -> RAGState:
    """Convert the question text into a vector embedding."""
    print(f"🔢 Embedding question: {state['question']}")
    embedding = await generate_embedding(state["question"])
    return {**state, "embedding": embedding}


# ─────────────────────────────────────────────
# Node 2: Retrieve similar chunks from ALL textbooks
# ─────────────────────────────────────────────

async def retrieve_chunks(state: RAGState) -> RAGState:
    """
    Similarity search across ALL stored textbooks — no class/subject filter.
    Students only provide a question; the system retrieves relevant content globally.
    """
    print(f"🔍 Searching all textbooks (top_k={state['top_k']})...")
    chunks = await vector_store.search_similar(
        query_embedding=state["embedding"],
        top_k=state["top_k"]
        # No class_filter or subject_filter → searches everything
    )
    print(f"✅ Retrieved {len(chunks)} chunks")
    return {**state, "chunks": chunks}


# ─────────────────────────────────────────────
# Node 3: Generate answer from retrieved context
# ─────────────────────────────────────────────

async def generate_answer(state: RAGState) -> RAGState:
    """Generate an exam-style answer from retrieved textbook chunks."""
    chunks = state["chunks"]

    if not chunks:
        return {
            **state,
            "answer": "No answer found in textbook.",
            "sources": [],
            "confidence": 0.0
        }

    # Average similarity of retrieved chunks as confidence
    confidence = round(
        sum(c["similarity"] for c in chunks) / len(chunks), 4
    )

    result = await gpt_service.generate_answer(state["question"], chunks)

    return {
        **state,
        "answer": result["answer"],
        "sources": result["sources"],
        "confidence": confidence
    }


# ─────────────────────────────────────────────
# Build the LangGraph graph
# ─────────────────────────────────────────────

def build_rag_graph():
    graph = StateGraph(RAGState)

    graph.add_node("embed_question", embed_question)
    graph.add_node("retrieve_chunks", retrieve_chunks)
    graph.add_node("generate_answer", generate_answer)

    graph.set_entry_point("embed_question")
    graph.add_edge("embed_question", "retrieve_chunks")
    graph.add_edge("retrieve_chunks", "generate_answer")
    graph.add_edge("generate_answer", END)

    return graph.compile()


# Compiled graph — import this in routes
rag_graph = build_rag_graph()
