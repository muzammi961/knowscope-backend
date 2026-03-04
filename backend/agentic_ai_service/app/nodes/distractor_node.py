# app/nodes/distractor_node.py

import random
from app.core.llm import get_llm
from app.utils.json_parser import safe_json_parse


async def generate_mcq(grounded_item: dict):
    """
    Generate exactly 3 distractors for a grounded correct answer,
    then shuffle 4 total options and assign correct_index.
    """
    question = grounded_item.get("question", "")
    correct_answer = grounded_item.get("answer", "")
    topic_id = grounded_item.get("topic_id", "")
    
    # Check if the generator passed down the full dictionary with conceptual tags
    # If the retrieval logic passes it properly.
    concept_tags = grounded_item.get("concept_tags", [])

    prompt = f"""
You are an expert MCQ generator formulating questions from retrieved context.

Question:
{question}

Correct Answer (grounded in context):
{correct_answer}

Generate exactly 3 plausible but incorrect distractors.

Rules:
- Distractors MUST be extremely short (maximum 15 words each). Each option must be a single concise phrase or number.
- Only ONE correct answer can exist. Ensure the 3 distractors are unambiguously incorrect but plausible.
- Must be the same short length and style as the correct answer.
- Must NOT repeat the correct answer or be synonymous with it.
- NO "All of the above", "None of the above", or "A and B" style options.
- Return STRICT JSON.

Output format:
{{
  "distractors": [
    "option1",
    "option2",
    "option3"
  ]
}}
"""

    llm = get_llm(temperature=0.7)
    response = await llm.ainvoke(prompt)

    data = safe_json_parse(response.content)

    if "distractors" not in data or len(data["distractors"]) != 3:
        raise ValueError("Invalid distractor format from LLM - must generate exactly 3 distractors.")

    distractors = data["distractors"]

    # Build exactly 4 options list
    options = distractors + [correct_answer]

    # Shuffle robustly
    random.shuffle(options)

    # Determine correct index
    correct_index = options.index(correct_answer)

    return {
        "question": question,
        "options": options,
        "correct_index": correct_index,
        "topic_id": topic_id,
        "concept_tags": concept_tags
    }