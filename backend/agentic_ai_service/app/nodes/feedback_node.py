# app/nodes/feedback_node.py

from app.core.llm import get_llm
from app.utils.json_parser import safe_json_parse
from app.schemas.evaluation import EvaluationState

async def generate_feedback(state: EvaluationState) -> EvaluationState:

    weak_questions = [
        item["question"]
        for item in state["details"]
        if not item["is_correct"]
    ]

    if not weak_questions:
        state["feedback"] = "Excellent performance. You've demonstrated a strong understanding of all tested concepts."
        return state

    prompt = f"""
You are an academic tutor providing feedback to a student.

Subject: {state['subject']}
Overall Score: {state['score']}% ({state['performance_level'].upper()})

The student answered the following questions incorrectly out of the total quiz:
{weak_questions}

Generate short, constructive feedback summarizing their test performance. 
- If their overall score is strong (e.g., above 70%), praise their high performance and mastery first, then gently note the minor areas they missed.
- If their overall score is average or weak, constructively summarize the core areas they failed in and explain that they need to review those topics.
Note: Do not provide actionable recommendations here, just a performance summary.

Return STRICT JSON:

{{
  "summary": "Short 1-2 sentence constructive summary..."
}}
"""

    llm = get_llm(temperature=0.3)
    response = await llm.ainvoke(prompt)

    parsed = safe_json_parse(response.content)
    state["feedback"] = parsed.get("summary", "Keep practicing the topics you struggled with.")
    
    return state