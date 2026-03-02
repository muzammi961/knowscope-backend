# app/nodes/question_node.py

import asyncio
from app.core.llm import get_llm
from app.utils.json_parser import safe_json_parse


async def generate_concept_questions(subject: str,
                                     topic: str | None,
                                     difficulty: str,
                                     num_questions: int):
    """
    Generate conceptual questions in batches to avoid rate limits.
    """
    if topic:
        focus_instruction = f"Focus strictly on the topic: {topic}. Output '{topic}' as the topic_id."
    else:
        focus_instruction = (
            "Distribute questions across different important topics "
            "from the subject syllabus. Output the specific topic as topic_id."
        )

    llm = get_llm(temperature=0.2)
    all_questions = []
    
    # We add a small buffer (+2) to ensure we hit num_questions
    target_count = num_questions + 2
    # Reduced batch size and increased delay to strictly respect 6000 TPM Groq limit
    batch_size = 3
    
    num_batches = (target_count + batch_size - 1) // batch_size
    
    for i in range(num_batches):
        current_batch_size = min(batch_size, target_count - (i * batch_size))
        
        prompt = f"""
You are an expert exam question generator.

Generate EXACTLY {current_batch_size} conceptual multiple choice QUESTIONS.

Subject: {subject}
Difficulty: {difficulty}

{focus_instruction}

RULES:
- Questions must be conceptual and non-trivial
- Avoid duplication
- Do NOT include explanations
- Do NOT include numbering
- Do NOT include extra text

CRITICAL:
Return ONLY valid JSON.
Do NOT include markdown.
Do NOT include ```json
Do NOT include any text before or after JSON.

Each question must contain:
- question
- topic_id
- concept_tags

Output format MUST be:

{{
  "questions": [
    {{
      "question": "text",
      "topic_id": "topic identifier",
      "concept_tags": ["tag1", "tag2"]
    }}
  ]
}}
"""

        if i > 0:
            # 6000 TPM = 100 tokens per second. We need enough time for tokens to replenish.
            await asyncio.sleep(4.5)
            
        try:
            response = await llm.ainvoke(prompt)
            data = safe_json_parse(response.content)

            if isinstance(data, dict) and "questions" in data:
                all_questions.extend(data["questions"])
        except Exception as e:
            print(f"Error in batch {i+1}: {e}")
            if "429" in str(e):
                # If we still hit a rate limit, back off heavily and retry the batch once
                print("Rate limit hit. Backing off for 10 seconds...")
                await asyncio.sleep(10)
                try:
                    response = await llm.ainvoke(prompt)
                    data = safe_json_parse(response.content)
                    if isinstance(data, dict) and "questions" in data:
                        all_questions.extend(data["questions"])
                except Exception as retry_e:
                    print(f"Retry failed for batch {i+1}: {retry_e}")
            continue

    if len(all_questions) < num_questions:
        raise ValueError(f"LLM generated fewer than {num_questions} questions. Only got {len(all_questions)}.")

    return all_questions[:num_questions]