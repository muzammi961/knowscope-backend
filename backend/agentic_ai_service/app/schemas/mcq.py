from pydantic import BaseModel, field_validator
from typing import List, Any


class MCQRequest(BaseModel):
    subject: str
    topic: str
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
    topic: str
    questions: List[MCQ]