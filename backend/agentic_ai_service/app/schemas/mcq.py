# app/schemas/mcq.py

from pydantic import BaseModel
from typing import List, Any, Optional


class MCQRequest(BaseModel):
    subject: str                  # e.g. "Maths", "Physics"
    class_level: str              # e.g. "10", "12"
    topic: str="Statistics"                    # free-form, user-provided e.g. "Statistics", "Optics"
    difficulty: str = "medium"   # "easy" | "medium" | "hard"
    num_questions: int = 20
    top_k: int = 6


class MCQ(BaseModel):
    question: str
    options: List[Any]
    correct_index: int
    topic_id: Optional[str] = None
    concept_tags: List[str] = []


class MCQResponse(BaseModel):
    quiz_id: str
    user_id: str
    subject: str
    class_level: str
    topic: str
    difficulty: str
    questions: List[MCQ]