# app/graphs/evaluation_graph.py

from app.services.quiz_repository import get_quiz_by_id
from app.nodes.scoring_node import evaluate_answers
from app.nodes.feedback_node import generate_feedback
from app.core.database import evaluations_collection
from datetime import datetime


async def run_evaluation_pipeline(quiz_id: str,
                                  user_answers: list[int]):

    quiz = await get_quiz_by_id(quiz_id)

    if not quiz:
        raise ValueError("Quiz not found")

    # 1️⃣ Deterministic scoring
    evaluation_result = evaluate_answers(quiz, user_answers)

    # 2️⃣ Generate feedback
    feedback = await generate_feedback(
        subject=quiz["subject"],
        topic=quiz["topic"],
        evaluation_result=evaluation_result
    )

    # 3️⃣ Store evaluation
    evaluation_doc = {
        "quiz_id": quiz_id,
        "subject": quiz["subject"],
        "score_percentage": evaluation_result["score_percentage"],
        "feedback": feedback,
        "created_at": datetime.utcnow()
    }

    await evaluations_collection.insert_one(evaluation_doc)

    return {
        "score": evaluation_result["score_percentage"],
        "correct_answers": evaluation_result["correct_answers"],
        "total_questions": evaluation_result["total_questions"],
        "feedback": feedback
    }