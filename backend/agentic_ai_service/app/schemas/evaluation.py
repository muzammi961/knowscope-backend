from pydantic import BaseModel
from typing import List


class EvaluationRequest(BaseModel):
    quiz_id: str
    user_answers: List[int]


class EvaluationResponse(BaseModel):
    quiz_id: str
    total_questions: int
    correct_answers: int
    score_percentage: float
    strong_areas: List[str]
    weak_areas: List[str]
    feedback: str
    improvement_suggestions: List[str]