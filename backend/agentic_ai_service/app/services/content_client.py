import httpx
from app.core.config import settings


async def query_content_service(question: str, top_k: int):
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.CONTENT_SERVICE_URL}/api/qa/ask",
            json={
                "question": question,
                "top_k": top_k
            }
        )

        response.raise_for_status()
        return response.json()