# app/schemas/dashboard.py
"""
Pydantic request/response schemas for all dashboard, study-session, and quiz-submit endpoints.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ── Study session ─────────────────────────────────────────────────────────────

class StudySessionRequest(BaseModel):
    subject: str
    duration_minutes: int = Field(..., ge=1)
    topics_covered: List[str] = Field(default_factory=list)


class StudySessionResponse(BaseModel):
    session_id: str
    message: str


# ── Quiz submit ───────────────────────────────────────────────────────────────

class QuizSubmitRequest(BaseModel):
    quiz_id: str
    subject: str
    class_level: str
    topic: str
    difficulty: str
    score_percentage: float = Field(..., ge=0, le=100)
    questions_answered: int = Field(..., ge=1)


class QuizSubmitResponse(BaseModel):
    message: str
    mastery_level: int          # 0-4 after this submission
    points_earned: int
    streak: int


# ── Heatmap ───────────────────────────────────────────────────────────────────

class HeatmapCell(BaseModel):
    date: str                   # "YYYY-MM-DD"
    mastery_level: int          # 0-6
    shade: str                  # Tailwind class e.g. "bg-gray-300"


class HeatmapResponse(BaseModel):
    cells: List[HeatmapCell]
    month_labels: List[Dict[str, Any]]  # [{month: "Jan", col_index: 0}, ...]


# ── Subject progress ──────────────────────────────────────────────────────────

class SubjectProgressItem(BaseModel):
    subject: str
    percentage: float


class SubjectProgressResponse(BaseModel):
    subjects: List[SubjectProgressItem]


# ── Topic analysis ────────────────────────────────────────────────────────────

class StrengthTopic(BaseModel):
    topic: str
    mastery_level: int


class WeaknessTopic(BaseModel):
    topic: str
    mastery_level: int
    has_data: bool


class TopicAnalysisResponse(BaseModel):
    strengths: List[StrengthTopic]
    weaknesses: List[WeaknessTopic]


# ── Overview / stats ──────────────────────────────────────────────────────────

class UserStatsModel(BaseModel):
    current_streak: int = 0
    longest_streak: int = 0
    total_points: int = 0
    rank: int = 9999
    focus_score: float = 0.0


class OverviewResponse(BaseModel):
    user_stats: UserStatsModel


# ── Activity feed ─────────────────────────────────────────────────────────────

class ActivityItem(BaseModel):
    activity_type: str          # "quiz" | "study"
    subject: str
    topic: Optional[str] = None
    score_percentage: Optional[float] = None
    duration_minutes: Optional[int] = None
    timestamp: str


class ActivityFeedResponse(BaseModel):
    activities: List[ActivityItem]
