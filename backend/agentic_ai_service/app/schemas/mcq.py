# app/schemas/mcq.py

from pydantic import BaseModel, field_validator
from typing import List, Any, Optional


class MCQRequest(BaseModel):
    subject: str                      # e.g. "Maths", "Physics"
    class_level: str                  # e.g. "10", "12" — used as context for question generation
    topic_id: str                     # e.g. "Trigonometry", "Optics" — student chooses freely
    difficulty: str = "medium"        # "easy" | "medium" | "hard"
    num_questions: int = 20
    top_k: int = 6


class MCQ(BaseModel):
    question: str
    options: List[Any]
    correct_index: int
    topic_id: Optional[str] = None
    concept_tags: List[str] = []

    @field_validator('options')
    def validate_options(cls, v):
        return [str(opt) for opt in v]


class MCQResponse(BaseModel):
    quiz_id: str
    user_id: str
    subject: str
    class_level: str
    topic: str                        # the topic used for generation
    difficulty: str
    questions: List[MCQ]