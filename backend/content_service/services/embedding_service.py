from sentence_transformers import SentenceTransformer
import asyncio

model = SentenceTransformer("BAAI/bge-small-en-v1.5")


async def generate_embedding(text: str) -> list[float]:
    loop = asyncio.get_running_loop()
    embedding = await loop.run_in_executor(
        None,
        lambda: model.encode(
            text,
            normalize_embeddings=True
        ).tolist()
    )
    return embedding
