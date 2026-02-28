# app/nodes/distractor_node.py

import random
from app.core.llm import get_llm
from app.utils.json_parser import safe_json_parse


async def generate_mcq(question: str, correct_answer: str):
    """
    Generate 3 distractors for a grounded correct answer,
    then shuffle options and assign correct_index.
    """

    prompt = f"""
You are an expert MCQ generator.

Question:
{question}

Correct Answer:
{correct_answer}

Generate exactly 3 plausible but incorrect distractors.

Rules:
- Distractors must be realistic.
- Same difficulty level as correct answer.
- Similar length/style.
- Must NOT repeat correct answer.
- No "All of the above" or "None of the above".
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
        raise ValueError("Invalid distractor format from LLM")

    distractors = data["distractors"]

    # Build options list
    options = distractors + [correct_answer]

    # Shuffle
    random.shuffle(options)

    # Determine correct index
    correct_index = options.index(correct_answer)

    return {
        "question": question,
        "options": options,
        "correct_index": correct_index,
        "correct_answer": correct_answer
    }