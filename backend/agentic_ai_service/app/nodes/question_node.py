# app/nodes/question_node.py

import asyncio
from app.core.llm import get_llm
from app.utils.json_parser import safe_json_parse


async def generate_concept_questions(subject: str,
                                     topic: str | None,
                                     difficulty: str,
                                     num_questions: int,
                                     class_level: str | None = None):
    """
    Generate conceptual questions in batches to avoid rate limits.
    Uses an academic prompt constrained to the given class syllabus.
    """
    llm = get_llm(temperature=0.2)
    all_questions = []

    # Buffer (+2) to ensure we hit num_questions after any filtering
    target_count = num_questions + 2
    # Reduced batch size to strictly respect 6000 TPM Groq limit
    batch_size = 3

    num_batches = (target_count + batch_size - 1) // batch_size

    for i in range(num_batches):
        current_batch_size = min(batch_size, target_count - (i * batch_size))

        # Build the class/topic focus context lines
        class_line = f"Class Level: {class_level}" if class_level else ""
        topic_line = f"Topic (focus strictly on this): {topic}" if topic else ""

        prompt = f"""
You are an expert academic question generator.

Generate {current_batch_size} unique, non-repeating questions based on the following criteria:

Subject: {subject}
{class_line}
{topic_line}
Difficulty: {difficulty}

Rules:
1. Questions must strictly belong to the given subject and class syllabus.
2. Do not repeat concepts.
3. Ensure conceptual variety.
4. Avoid duplicate or similar phrasing.
5. Maintain curriculum-level accuracy.
6. Output must be valid JSON format.

CRITICAL:
Return ONLY valid JSON.
Do NOT include markdown or ```json blocks.
Do NOT include any text before or after the JSON.

Each question object MUST contain:
- "question"    : the question text
- "difficulty"  : the difficulty level
- "topic"       : the specific curriculum topic or chapter name
- "type"        : "mcq" (always use "mcq" for this pipeline)
- "concept_tags": list of 2-4 related concept keywords

Output format MUST be:

{{
  "questions": [
    {{
      "question": "...",
      "difficulty": "...",
      "topic": "...",
      "type": "mcq",
      "concept_tags": ["tag1", "tag2"]
    }}
  ]
}}
"""

        if i > 0:
            # 6000 TPM = 100 tokens/sec. Need time for tokens to replenish.
            await asyncio.sleep(4.5)

        try:
            response = await llm.ainvoke(prompt)
            data = safe_json_parse(response.content)

            if isinstance(data, dict) and "questions" in data:
                # Normalize: map 'topic' → 'topic_id' for downstream pipeline compatibility
                for q in data["questions"]:
                    if "topic" in q and "topic_id" not in q:
                        q["topic_id"] = q["topic"]
                all_questions.extend(data["questions"])

        except Exception as e:
            print(f"Error in batch {i+1}: {e}")
            if "429" in str(e):
                print("Rate limit hit. Backing off for 10 seconds...")
                await asyncio.sleep(10)
                try:
                    response = await llm.ainvoke(prompt)
                    data = safe_json_parse(response.content)
                    if isinstance(data, dict) and "questions" in data:
                        for q in data["questions"]:
                            if "topic" in q and "topic_id" not in q:
                                q["topic_id"] = q["topic"]
                        all_questions.extend(data["questions"])
                except Exception as retry_e:
                    print(f"Retry failed for batch {i+1}: {retry_e}")
            continue

    if len(all_questions) < num_questions:
        raise ValueError(
            f"LLM generated fewer than {num_questions} questions. "
            f"Only got {len(all_questions)}."
        )

    return all_questions[:num_questions]