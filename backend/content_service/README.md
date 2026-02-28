# 📚 Knowscope Content Service — RAG Textbook Q&A

A fully automated **Retrieval-Augmented Generation (RAG)** system that lets students ask questions from their textbooks and receive accurate, exam-style answers — automatically.

```
Teacher uploads PDF  →  System processes & indexes textbook
Student asks question  →  System retrieves relevant content  →  GPT generates answer
```

---

## 🏗️ Architecture

```
PDF Upload ──► pdf_loader ──► text_cleaner ──► chapter_pipeline
                                                      │
                                               topic_extractor
                                                      │
                                               chunk_builder ──► embedding_service
                                                                        │
                                                                   ChromaDB (vector DB)
                                                                        │
Student Question ──► LangGraph RAG Graph ──► embed_question
                                                  │
                                            retrieve_chunks  ←── ChromaDB
                                                  │
                                            generate_answer  ──► OpenAI GPT
                                                  │
                                          Exam-style Answer ──► Student
```

**Stack:**
| Component | Technology |
|---|---|
| Backend API | FastAPI |
| Vector Database | ChromaDB (persistent, local) |
| Embeddings | SentenceTransformers (`BAAI/bge-small-en-v1.5`) |
| RAG Orchestration | LangGraph |
| LLM | OpenAI GPT-3.5-Turbo |
| PDF Parsing | pdfplumber |
| Document Store | MongoDB (Atlas) |

---

## ⚙️ Setup

### 1. Prerequisites
- Python 3.10+
- MongoDB Atlas cluster (URI in `.env`)
- OpenAI API key (optional — fallback returns raw text chunks)

### 2. Install Dependencies

```powershell
cd backend\content_service
python -m venv content_venv
.\content_venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment

Edit `.env`:
```env
MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=knowscope
MONGO_DB=knowscope
OPENAI_API_KEY=sk-...your-real-key-here...
```

> **Note:** Without `OPENAI_API_KEY`, the system falls back to returning the most relevant raw textbook passages.

### 4. Run the Server

```powershell
cd backend\content_service
.\content_venv\Scripts\activate
uvicorn app.main:app --reload --port 8001
```

API docs available at: **http://localhost:8001/docs**

---

## 📡 API Reference

### 📤 Ingestion (Teacher / Admin)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ingest/pdf` | Upload a PDF textbook and index it |
| `GET` | `/ingest/books` | List all ingested books |
| `DELETE` | `/ingest/book/{book_id}` | Remove a book from all stores |

#### Upload PDF
```bash
curl -X POST http://localhost:8001/ingest/pdf \
  -F "file=@textbook.pdf" \
  -F "book_id=biology_class10" \
  -F "class_number=10" \
  -F "subject=biology"
```

Response:
```json
{
  "message": "✅ PDF ingested successfully",
  "book_id": "biology_class10",
  "pages_extracted": 248,
  "chapters_created": 12,
  "total_chunks_indexed": 387
}
```

---

### ❓ Question Answering (Student)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/qa/ask` | Ask a question — full RAG answer |
| `POST` | `/api/qa/search` | Retrieve raw chunks (no LLM) |
| `GET` | `/api/qa/stats` | ChromaDB statistics |
| `GET` | `/api/qa/books` | List indexed books in ChromaDB |
| `DELETE` | `/api/qa/book/{book_id}` | Remove book vectors |

#### Ask a Question (Student provides ONLY the question)
```bash
curl -X POST http://localhost:8001/api/qa/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain photosynthesis."}'
```

Response:
```json
{
  "answer": "Photosynthesis is the process by which green plants use sunlight...",
  "sources": [
    {
      "chapter": "Life Processes",
      "topic": "Photosynthesis",
      "similarity": 0.923,
      "text_preview": "Photosynthesis is the process by which..."
    }
  ],
  "confidence": 0.887,
  "total_chunks_used": 5
}
```

---

## 🧪 Testing

### Verify all imports
```powershell
python scripts/verify_setup.py
```

### End-to-end RAG pipeline test
```powershell
python scripts/test_qa.py
```
This seeds 3 photosynthesis chunks, runs embedding → search → GPT answer → cleanup.

---

## 📂 Project Structure

```
content_service/
├── app/
│   ├── main.py            # FastAPI app + lifespan
│   ├── database.py        # MongoDB (Motor) collections
│   ├── vector_store.py    # ChromaDB wrapper
│   └── models.py          # Pydantic models
├── routes/
│   ├── ingest.py          # PDF upload endpoints
│   └── qa.py              # Q&A endpoints
├── services/
│   ├── pdf_loader.py      # PDF text extraction
│   ├── chapter_pipeline.py # TOC-based chapter splitting
│   ├── topic_extractor.py  # Topic segmentation
│   ├── chunk_builder.py    # Chunking + embedding + storage
│   ├── embedding_service.py # SentenceTransformer wrapper
│   ├── rag_graph.py        # LangGraph RAG pipeline
│   └── gpt_service.py      # OpenAI GPT answer generation
├── utils/
│   └── text_cleaner.py     # Generic PDF text cleaning
├── scripts/
│   ├── test_qa.py          # End-to-end RAG test
│   └── verify_setup.py     # Import verification
├── chroma_db_data/         # ChromaDB persistent storage (auto-created)
├── requirements.txt
└── .env
```

---

## 💡 How It Works

### PDF Ingestion
1. PDF text is extracted page-by-page using `pdfplumber`
2. Text is cleaned (page numbers, artifacts, repeated headers removed)
3. Table of Contents is detected and used to split into chapters
4. Chapters are further segmented by topic using paragraph detection
5. Each topic is split into 400-word chunks with 50-word overlap
6. Chunks are embedded using `BAAI/bge-small-en-v1.5` (384-dim vectors)
7. Vectors are stored in ChromaDB; raw text is stored in MongoDB

### Student Q&A (RAG Pipeline)
1. Student question is embedded with the same model
2. ChromaDB performs cosine similarity search across **all** stored textbooks
3. Top-K most relevant chunks are retrieved as context
4. GPT-3.5-Turbo generates a structured exam-style answer based **only** on retrieved context
5. If no relevant content found (confidence < 0.25), returns `"No answer found in textbook."`
