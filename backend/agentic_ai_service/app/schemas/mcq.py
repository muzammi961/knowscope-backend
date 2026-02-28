from pydantic import BaseModel
from typing import List


class MCQRequest(BaseModel):
    subject: str
    topic: str
    difficulty: str
    num_questions: int
    top_k: int = 5


class MCQ(BaseModel):
    question: str
    options: List[str]
    correct_index: int


class MCQResponse(BaseModel):
    quiz_id: str
    subject: str
    topic: str
    questions: List[MCQ]