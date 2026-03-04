from pydantic import BaseModel, field_validator
from typing import List, Any


class MCQRequest(BaseModel):
    subject: str
    class_level: str          # e.g. "Class 10" — maps to a topic automatically
    difficulty: str
    num_questions: int = 20
    top_k: int = 6


class MCQ(BaseModel):
    question: str
    options: List[Any]
    correct_index: int
    topic_id: str | None = None
    concept_tags: List[str] = []

    @field_validator('options')
    def validate_options(cls, v):
        return [str(opt) for opt in v]


class MCQResponse(BaseModel):
    quiz_id: str
    subject: str
    class_level: str          # echoed back from the request
    topic: str                # the resolved topic_id that was used
    questions: List[MCQ]
    