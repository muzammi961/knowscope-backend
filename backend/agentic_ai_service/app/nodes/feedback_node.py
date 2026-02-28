# app/nodes/feedback_node.py

from app.core.llm import get_llm
from app.utils.json_parser import safe_json_parse


async def generate_feedback(subject: str, evaluation_result: dict):

    weak_questions = [
        item["question"]
        for item in evaluation_result["details"]
        if not item["is_correct"]
    ]

    if not weak_questions:
        return {
            "summary": "Excellent performance.",
            "improvement_areas": [],
            "recommendation": "Keep practicing advanced problems."
        }

    prompt = f"""
You are an academic tutor.

Subject: {subject}

The student answered the following questions incorrectly:
{weak_questions}

Generate structured feedback.

Return STRICT JSON:

{{
  "summary": "...",
  "improvement_areas": ["area1", "area2"],
  "recommendation": "..."
}}
"""

    llm = get_llm(temperature=0.3)
    response = await llm.ainvoke(prompt)

    return safe_json_parse(response.content)