"""
End-to-end RAG pipeline test script
=====================================
Run from the content_service directory:
    python scripts/test_qa.py

What it does:
  1. Seeds ChromaDB with 3 synthetic textbook chunks.
  2. Searches for a sample question using the embedding model.
  3. Calls GPT to generate an answer (or falls back if no API key).
  4. Prints results for manual inspection.
  5. Cleans up seeded data after the test.
"""

import sys
import os
import asyncio

# ── Path setup ──────────────────────────────────────────────
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, parent_dir)

# Provide mock env vars for testing (does not overwrite real values)
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB", "test_db")

# ── Sample textbook data ─────────────────────────────────────
SAMPLE_BOOK_ID = "__test_rag_book__"
SAMPLE_CHUNKS_TEXT = [
    (
        "Photosynthesis is the process by which green plants and some other organisms "
        "use sunlight to synthesize foods with carbon dioxide and water. "
        "Photosynthesis in plants generally involves the green pigment chlorophyll and "
        "generates oxygen as a byproduct. The overall chemical equation is: "
        "6CO2 + 6H2O + light energy → C6H12O6 + 6O2."
    ),
    (
        "Chloroplasts are organelles found in plant cells where photosynthesis takes place. "
        "They contain the pigment chlorophyll, which absorbs light energy, primarily from "
        "the blue and red parts of the light spectrum. The light-dependent reactions occur "
        "in the thylakoid membranes, while the Calvin cycle (light-independent reactions) "
        "occurs in the stroma."
    ),
    (
        "The rate of photosynthesis is affected by several factors: light intensity, "
        "carbon dioxide concentration, water availability, and temperature. "
        "At low light intensity, photosynthesis rate increases as light increases. "
        "At very high temperatures, enzyme activity decreases and photosynthesis slows down."
    )
]

METADATA_TEMPLATES = [
    {"chapter_index": "1", "chapter_title": "Life Processes", "topic_index": "1",
     "topic_title": "Photosynthesis", "chunk_index": "1",
     "book_id": SAMPLE_BOOK_ID, "class": "10", "subject": "science"},
    {"chapter_index": "1", "chapter_title": "Life Processes", "topic_index": "1",
     "topic_title": "Chloroplasts", "chunk_index": "2",
     "book_id": SAMPLE_BOOK_ID, "class": "10", "subject": "science"},
    {"chapter_index": "1", "chapter_title": "Life Processes", "topic_index": "2",
     "topic_title": "Factors Affecting Photosynthesis", "chunk_index": "1",
     "book_id": SAMPLE_BOOK_ID, "class": "10", "subject": "science"},
]


async def run_test():
    print("\n" + "=" * 60)
    print("  [TEST] KnowScope RAG Pipeline - End-to-End Test")
    print("=" * 60)

    # Import after path setup
    from services.embedding_service import generate_embedding
    from app.vector_store import vector_store, collection

    # Track seeded IDs for cleanup
    seeded_ids = []

    try:
        # -- Step 1: Seed ChromaDB --------------------------------
        print("\n[SEED] Seeding ChromaDB with 3 sample textbook chunks...")
        ids, embeddings, documents, metadatas = [], [], [], []

        for i, (text, meta) in enumerate(zip(SAMPLE_CHUNKS_TEXT, METADATA_TEMPLATES)):
            chunk_id = f"{SAMPLE_BOOK_ID}_test_chunk_{i+1}"
            emb = await generate_embedding(text)
            ids.append(chunk_id)
            embeddings.append(emb)
            documents.append(text)
            metadatas.append(meta)
            print(f"   [OK] Embedded chunk {i+1}/3")

        seeded_ids = list(ids)
        collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        print(f"\n[OK] Seeded {len(ids)} chunks into ChromaDB")
        print(f"   Total chunks in store: {collection.count()}")

        # ── Step 2: Run similarity search ─────────────────────────
        question = "Explain photosynthesis."
        print(f"\n🔍 Question: \"{question}\"")
        print("   Generating question embedding...")
        q_embedding = await generate_embedding(question)

        chunks = await vector_store.search_similar(query_embedding=q_embedding, top_k=3)
        print(f"\n📄 Retrieved {len(chunks)} chunks:")
        for i, c in enumerate(chunks):
            print(f"\n   [{i+1}] Similarity: {c['similarity']:.4f}")
            print(f"       Topic: {c['metadata'].get('topic_title', 'N/A')}")
            print(f"       Preview: {c['text'][:120]}...")

        # ── Step 3: Generate answer ─────────────────────────────
        print("\n[LLM] Generating answer...")
        from services.gpt_service import gpt_service
        result = await gpt_service.generate_answer(question, chunks)
        print("\n" + "-" * 60)
        print("GENERATED ANSWER:")
        print("-" * 60)
        print(result["answer"])
        print("─" * 60)

        # ── Step 4: Run full LangGraph pipeline ──────────────────
        print("\n🔗 Testing full LangGraph RAG graph...")
        from services.rag_graph import rag_graph
        graph_result = await rag_graph.ainvoke({
            "question": question,
            "top_k": 3,
            "embedding": [],
            "chunks": [],
            "answer": "",
            "sources": [],
            "confidence": 0.0
        })
        print(f"   Confidence: {graph_result['confidence']}")
        print(f"   Chunks used: {len(graph_result['chunks'])}")
        print(f"   Answer preview: {graph_result['answer'][:200]}...")

        print("\n[OK] All tests passed!")

    finally:
        # ── Cleanup: remove seeded test data from ChromaDB ───────
        if seeded_ids:
            print("\n[CLEANUP] Removing seeded test chunks from ChromaDB...")
            try:
                collection.delete(ids=seeded_ids)
                print(f"   Removed {len(seeded_ids)} test chunks")
            except Exception as cleanup_err:
                print(f"   ⚠️ Cleanup warning: {cleanup_err}")
        print()


if __name__ == "__main__":
    asyncio.run(run_test())
