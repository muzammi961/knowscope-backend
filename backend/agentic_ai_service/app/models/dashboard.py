# app/models/dashboard.py
"""
MongoDB document models for the student dashboard system.
Uses Pydantic for validation; Motor (async MongoDB) for persistence.
Collections:
  - user_progress
  - subject_progress
  - topic_mastery
  - activity_heatmap
  - dashboard_notifications
  - learning_activities
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────

class MasteryStatus(str, Enum):
    MASTERED    = "Mastered"
    IN_PROGRESS = "In Progress"
    STRUGGLING  = "Struggling"
    NOT_STARTED = "Not Started"


class NotificationType(str, Enum):
    EXAM              = "exam"
    DOUBT_RESOLUTION  = "doubt_resolution"
    RESOURCE          = "resource"
    INSIGHT           = "insight"


# ── Embedded sub-documents ────────────────────────────────────────────────────

class WeeklyDataPoint(BaseModel):
    """One day's data point for the weekly progress line graph."""
    date: str           # ISO date string  e.g. "2026-03-12"
    score: float = 0.0  # 0-100 progress score for that day
    minutes: int = 0    # minutes studied that day


class HeatmapCell(BaseModel):
    """A single day cell in the 52-week activity heatmap."""
    date: str           # ISO date string
    intensity: int = 0  # 0–6  (0 = no activity, 6 = max)
    minutes: int = 0    # minutes studied


class SubjectStat(BaseModel):
    subject: str
    mastery_pct: float = 0.0    # 0-100
    time_spent_minutes: int = 0
    topics_total: int = 0
    topics_mastered: int = 0


# ── Top-level documents ───────────────────────────────────────────────────────

class UserProgress(BaseModel):
    """
    Top-level user dashboard state.
    MongoDB collection: user_progress
    """
    user_id: str
    current_class: str = "Class 11"
    section: str = "A"
    current_topic: str = "Not Set"
    current_subject: str = "Physics"

    # Gamification
    total_points: int = 0
    ranking: int = 9999
    current_streak: int = 0       # consecutive days
    longest_streak: int = 0
    focus_score: float = 0.0      # 0-100 composite score

    # Weekly progress (last 7 days)
    weekly_data: List[WeeklyDataPoint] = Field(default_factory=list)

    # Syllabus completion 0-100
    syllabus_completion_pct: float = 0.0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class SubjectProgress(BaseModel):
    """
    Per-subject progress record.
    MongoDB collection: subject_progress
    One document per (user_id, subject) pair.
    """
    user_id: str
    subject: str                          # "Physics", "Chemistry", "Math", "Biology"
    mastery_pct: float = 0.0              # 0-100
    time_spent_minutes: int = 0
    topics_total: int = 0
    topics_mastered: int = 0
    last_studied_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TopicMastery(BaseModel):
    """
    Per-topic mastery record.
    MongoDB collection: topic_mastery
    One document per (user_id, topic_id) pair.
    """
    user_id: str
    topic_id: str
    topic_name: str
    subject: str
    mastery_pct: float = 0.0           # 0-100
    status: MasteryStatus = MasteryStatus.NOT_STARTED
    time_spent_minutes: int = 0
    sessions_count: int = 0
    last_studied_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class ActivityHeatmap(BaseModel):
    """
    52-week activity heatmap.
    MongoDB collection: activity_heatmap
    One document per user_id (contains cells list).
    """
    user_id: str
    year: int
    cells: List[HeatmapCell] = Field(default_factory=list)  # up to 365 cells

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DashboardNotification(BaseModel):
    """
    AI-generated notification.
    MongoDB collection: dashboard_notifications
    """
    user_id: str
    notification_type: NotificationType
    title: str
    message: str
    is_read: bool = False
    icon: Optional[str] = None          # emoji or icon key for frontend

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class LearningActivity(BaseModel):
    """
    Single recent learning activity entry.
    MongoDB collection: learning_activities
    """
    user_id: str
    subject: str
    topic_id: str
    topic_name: str
    mastery_pct: float = 0.0
    time_spent_minutes: int = 0
    status: MasteryStatus = MasteryStatus.IN_PROGRESS

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
