# app/services/quiz_repository.py

from datetime import datetime
from bson import ObjectId
from app.core.database import quizzes_collection


async def save_quiz(
    user_id: str,
    subject: str,
    class_level: str,
    topic: str,
    difficulty: str,
    questions: list,
) -> str:
    """Store a generated quiz in MongoDB under the user's account."""
    quiz_doc = {
        "user_id":       user_id,
        "subject":       subject,
        "class_level":   class_level,
        "topic":         topic,
        "difficulty":    difficulty,
        "questions":     questions,
        "num_questions": len(questions),
        "created_at":    datetime.utcnow(),
    }
    result = await quizzes_collection.insert_one(quiz_doc)
    return str(result.inserted_id)


async def get_quiz_by_id(quiz_id: str) -> dict | None:
    try:
        quiz = await quizzes_collection.find_one({"_id": ObjectId(quiz_id)})
    except Exception:
        return None
    if not quiz:
        return None
    quiz["_id"] = str(quiz["_id"])
    return quiz


async def get_quizzes_by_user(user_id: str, limit: int = 20) -> list[dict]:
    cursor = quizzes_collection.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    quizzes = []
    async for q in cursor:
        q["_id"] = str(q["_id"])
        quizzes.append(q)
    return quizzes