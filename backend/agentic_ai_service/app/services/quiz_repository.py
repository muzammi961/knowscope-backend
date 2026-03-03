# app/services/quiz_repository.py

from datetime import datetime
from bson import ObjectId
from app.core.database import quizzes_collection


async def save_quiz(subject: str,
                    topic: str | None,
                    difficulty: str,
                    questions: list):
    """
    Store quiz in MongoDB.
    """

    quiz_doc = {
        "subject": subject,
        "topic": topic,
        "difficulty": difficulty,
        "questions": questions,
        "created_at": datetime.utcnow()
    }

    result = await quizzes_collection.insert_one(quiz_doc)

    return str(result.inserted_id)


async def get_quiz_by_id(quiz_id: str):
    """
    Fetch quiz by ID.
    """
    quiz = await quizzes_collection.find_one({"_id": ObjectId(quiz_id)})

    if not quiz:
        return None

    quiz["_id"] = str(quiz["_id"])
    return quiz