# app/nodes/retrieval_node.py

import asyncio
from app.core.config import settings
from app.services.content_client import query_content_service


async def _retrieve_single(question: str,
                           subject: str,
                           topic: str | None,
                           top_k: int,
                           max_retries: int = 2):
    """
    Retrieve grounded answer for a single question.
    Retry max 2 times if confidence < threshold.
    """

    # Inject subject/topic into query for better retrieval
    if topic:
        query = f"{subject} - {topic}: {question}"
    else:
        query = f"{subject}: {question}"

    for _ in range(max_retries + 1):
        result = await query_content_service(question=query, top_k=top_k)

        if not result:
            continue

        confidence = result.get("confidence", 0)
        answer = result.get("answer")

        if confidence >= settings.CONFIDENCE_THRESHOLD and answer:
            return {
                "question": question,
                "answer": answer,
                "confidence": confidence
            }

    return None  # failed after retries


async def retrieve_valid_questions(questions: list[str],
                                   subject: str,
                                   topic: str | None,
                                   top_k: int,
                                   required_count: int):
    """
    Runs retrieval in parallel and returns only valid grounded questions.
    Stops when required_count reached.
    """

    tasks = [
        _retrieve_single(q, subject, topic, top_k)
        for q in questions
    ]

    results = await asyncio.gather(*tasks)
    print(results)

    # Filter valid
    valid = [r for r in results if r is not None]

    # Return only required_count
    return valid[:required_count]