import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import os

# Initialize ChromaDB client with persistent storage
chroma_client = chromadb.PersistentClient(
    path="./chroma_db_data",  # Vector DB stored here
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=True
    )
)

# Get or create collection — NEVER delete on startup so indexed data persists
collection = chroma_client.get_or_create_collection(
    name="knowscope_chunks",
    metadata={"hnsw:space": "cosine"}  # Use cosine similarity
)

class VectorStore:
    @staticmethod
    async def add_chunks(chunks: List[Dict[str, Any]]):
        """
        Add chunks to ChromaDB vector store
        """
        if not chunks:
            return 0
            
        ids = []
        embeddings = []
        metadatas = []
        documents = []
        
        for i, chunk in enumerate(chunks):
            # Create unique ID
            chunk_id = f"{chunk['book_id']}_ch{chunk['chapter_index']}_t{chunk['topic_index']}_c{chunk['chunk_index']}"
            
            ids.append(chunk_id)
            embeddings.append(chunk['embedding'])
            documents.append(chunk['text'])
            
            # Store metadata for filtering
            metadatas.append({
                "book_id": chunk['book_id'],
                "class": str(chunk.get('class', '0')),  # ChromaDB requires strings
                "subject": chunk.get('subject', ''),
                "chapter_index": str(chunk['chapter_index']),
                "chapter_title": chunk.get('chapter_title', ''),
                "topic_index": str(chunk['topic_index']),
                "topic_title": chunk.get('topic_title', ''),
                "chunk_index": str(chunk['chunk_index'])
            })
        
        # Add to ChromaDB in batches (to avoid memory issues)
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_end = min(i + batch_size, len(ids))
            collection.add(
                ids=ids[i:batch_end],
                embeddings=embeddings[i:batch_end],
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end]
            )
        
        return len(chunks)
    
    @staticmethod
    async def search_similar(
        query_embedding: List[float],
        class_filter: Optional[int] = None,
        subject_filter: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search similar chunks with metadata filters
        """
        # Build where clause for filtering
        where_clause = {}
        if class_filter is not None:
            where_clause["class"] = str(class_filter)
        if subject_filter:
            where_clause["subject"] = subject_filter.lower()
        
        try:
            # Query ChromaDB
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    # Convert distance to similarity score (cosine distance to cosine similarity)
                    similarity = 1 - results['distances'][0][i] if results['distances'][0][i] <= 1 else 0
                    
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'similarity': round(similarity, 4)
                    })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching vector store: {e}")
            return []
    
    @staticmethod
    async def delete_book_chunks(book_id: str):
        """
        Delete all chunks for a specific book
        """
        try:
            collection.delete(
                where={"book_id": book_id}
            )
            return True
        except Exception as e:
            print(f"Error deleting chunks: {e}")
            return False
    
    @staticmethod
    async def get_stats():
        """
        Get statistics about the vector store
        """
        try:
            count = collection.count()
            return {
                "total_chunks": count,
                "collection_name": "knowscope_chunks",
                "status": "active"
            }
        except Exception as e:
            return {
                "total_chunks": 0,
                "status": f"error: {str(e)}"
            }

# Initialize vector store
vector_store = VectorStore()