# app/nodes/retrieval_node.py

import asyncio
from app.core.config import settings
from app.services.content_client import query_content_service
from app.core.llm import get_llm
from app.utils.json_parser import safe_json_parse


async def _fallback_generate_answer(question_text: str, subject: str, topic: str | None) -> str:
    """Generate an answer directly from the LLM without RAG if retrieval fails."""
    llm = get_llm(temperature=0.3)
    topic_str = f" on the topic of {topic}" if topic else ""
    prompt = f"""
You are an expert in {subject}{topic_str}.
Provide a concise, accurate factual answer to the following question.

Question: {question_text}

Rules:
- Give a direct, fact-based answer.
- Limit your answer to a MAXIMUM of 15 words. Keep it extremely short, like a flashcard.
- Return ONLY valid JSON.

Output format MUST be:
{{
  "answer": "your factual answer here"
}}
"""
    try:
        response = await llm.ainvoke(prompt)
        data = safe_json_parse(response.content)
        return data.get("answer", "")
    except Exception as e:
        print(f"Fallback generation failed: {e}")
        if "429" in str(e):
            print("Fallback hit 429 Rate Limit. Backing off for 12 seconds...")
            await asyncio.sleep(12)
            try:
                response = await llm.ainvoke(prompt)
                data = safe_json_parse(response.content)
                return data.get("answer", "")
            except Exception as retry_e:
                print(f"Fallback retry failed: {retry_e}")
        return ""


async def _retrieve_single(question: dict,
                           subject: str,
                           topic: str | None,
                           top_k: int,
                           max_retries: int = 2):
    """
    Retrieve grounded answer for a single question.
    Retry max 2 times if confidence < threshold.
    If RAG fails or service hits 429, fallback to generating an out-of-syllabus answer.
    """
    
    # Extract topic_id or chapter_id if available to support fallback
    topic_id = question.get("topic_id", topic)
    chapter_id = question.get("chapter_id", subject)
    q_text = question["question"] if isinstance(question, dict) else question
    
    # Inject subject/topic into query for better retrieval
    if topic:
        query = f"{subject} - {topic}: {q_text}"
    else:
        query = f"{subject}: {q_text}"

    for attempt in range(max_retries + 1):
        # Attempt standard retrieval first, fallback on subsequent attempts
        if attempt > 0:
            # Fallback retrieval using metadata if available
            fallback_query = f"topic_id: {topic_id} OR chapter_id: {chapter_id}"
            result = await query_content_service(question=fallback_query, top_k=top_k)
        else:
            result = await query_content_service(question=query, top_k=top_k)

        if not result:
            continue

        confidence = result.get("confidence", 0)
        answer = result.get("answer", "")
        
        # Validation step: Protect against Content Service passing off API errors directly as text context
        if "Error generating answer" in answer or "429" in answer:
            continue

        # Validation step: If retrieved_context < minimum length, retry using fallback
        if len(answer) < 200:
            continue

        if confidence >= settings.CONFIDENCE_THRESHOLD and answer:
            return {
                "question": q_text,
                "answer": answer,
                "confidence": confidence,
                "topic_id": topic_id
            }

    # If RAG fails entirely, fallback to zero-shot generation
    print(f"RAG failed for: {q_text}. Generating fallback answer directly...")
    fallback_answer = await _fallback_generate_answer(q_text, subject, topic)
    
    if fallback_answer:
        return {
            "question": q_text,
            "answer": fallback_answer,
            "confidence": 0.5, # Indicator that this was a fallback
            "topic_id": topic_id
        }

    return None  # failed completely


async def retrieve_valid_questions(questions: list,
                                   subject: str,
                                   topic: str | None,
                                   top_k: int = 4,
                                   required_count: int = 20):
    """
    Runs retrieval in parallel and returns only valid grounded questions.
    Batches execution to avoid hitting rate limits on the external service or our LLM fallbacks.
    Stops when required_count reached.
    """
    results = []
    batch_size = 5
    
    for i in range(0, len(questions), batch_size):
        batch = questions[i:i + batch_size]
        tasks = [
            _retrieve_single(q, subject, topic, top_k)
            for q in batch
        ]
        
        if i > 0:
            await asyncio.sleep(2.5)
            
        print(f"Retrieving context for batch {i//batch_size + 1} / {(len(questions) + batch_size - 1)//batch_size}...")
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)

    print("========== RETRIEVAL RESULTS ==========")
    valid = [r for r in results if r is not None]
    print(f"Successfully retrieved/generated context for {len(valid)} questions.")
    print("=======================================")

    if len(valid) == 0:
        raise ValueError("Retrieval failed to ground any questions. Empty context cannot proceed to MCQ generator.")

    # Return only required_count
    return valid[:required_count]