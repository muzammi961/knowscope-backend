# app/schemas/evaluation.py

from pydantic import BaseModel
from typing import List, Dict, Any, TypedDict, Union
import operator
from typing import Annotated


class UserAnswer(BaseModel):
    question: str
    selected_option: str


class EvaluationRequest(BaseModel):
    student_id: str
    quiz_id: str
    # Accept either the index (int) or the structured object for ease of use
    user_answers: List[Union[int, UserAnswer]]


class EvaluationResponse(BaseModel):
    quiz_id: str
    total_questions: int
    correct_answers: int
    score_percentage: float
    strong_areas: List[str]
    weak_areas: List[str]
    feedback: str
    # improvement_suggestions: List[str]
    recommendations: str = ""


class EvaluationState(TypedDict):
    """LangGraph State Object for Evaluation"""
    student_id: str
    quiz_id: str
    subject: str
    topic: str
    answers: List[Union[int, Dict[str, str]]]
    correct_answers: int
    total_questions: int
    score: float
    weak_topics: List[str]
    strong_topics: List[str]
    performance_level: str
    recommendations: str
    feedback: str
    quiz_data: Dict[str, Any]  # The loaded quiz
    details: List[Dict[str, Any]]