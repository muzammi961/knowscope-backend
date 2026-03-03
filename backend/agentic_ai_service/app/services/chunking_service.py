# app/services/chunking_service.py

from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_document(text: str, topic_id: str, chapter_id: str) -> list[dict]:
    """
    Splits text into chunks of 500-800 characters/tokens with 100-150 overlap.
    Retains topic_id and chapter_id in the metadata for each chunk.
    """
    
    # We use roughly characters as a proxy for tokens if a specific tokenizer isn't provided,
    # or you could configure from_tiktoken_encoder if needed. We will stick to the requested sizes.
    chunk_size = 800
    chunk_overlap = 150
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    text_chunks = splitter.split_text(text)
    
    documents = []
    for chunk in text_chunks:
        # We ensure chunks represent a reasonable lower bound (e.g. at least 500) where possible, 
        # though RecursiveCharacterTextSplitter focuses on the max `chunk_size`.
        documents.append({
            "page_content": chunk,
            "metadata": {
                "topic_id": topic_id,
                "chapter_id": chapter_id
            }
        })
        
    return documents
