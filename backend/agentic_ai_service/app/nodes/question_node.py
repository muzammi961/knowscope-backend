# app/nodes/question_node.py

from app.core.llm import get_llm
from app.utils.json_parser import safe_json_parse


async def generate_concept_questions(subject: str,
                                     topic: str | None,
                                     difficulty: str,
                                     num_questions: int):
    """
    Generate conceptual questions only (NO options yet).
    We generate buffer = num_questions + 5
    """

    buffer_size = num_questions + 5

    if topic:
        focus_instruction = f"Focus strictly on the topic: {topic}."
    else:
        focus_instruction = (
            "Distribute questions across different important topics "
            "from the subject syllabus. Avoid repeating same chapter."
        )

    prompt = f"""
You are an expert exam question generator.

Generate {buffer_size} conceptual multiple choice QUESTIONS (questions only, no options).

Subject: {subject}
Difficulty: {difficulty}

{focus_instruction}

Rules:
- Questions must be clear and conceptual.
- Avoid duplication.
- Avoid trivial definitions.
- Return STRICT JSON.
- Do NOT include explanations.

Output format:
{{
  "questions": [
    "Question 1",
    "Question 2"
  ]
}}
"""

    llm = get_llm(temperature=0.5)

    response = await llm.ainvoke(prompt)

    data = safe_json_parse(response.content)

    if "questions" not in data:
        raise ValueError("LLM did not return questions field")

    return data["questions"]