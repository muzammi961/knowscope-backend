# app/schemas/dashboard.py
"""
Pydantic request/response schemas for the dashboard API.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ── Shared enums ─────────────────────────────────────────────────────────────

class NotificationType(str, Enum):
    EXAM             = "exam"
    DOUBT_RESOLUTION = "doubt_resolution"
    RESOURCE         = "resource"
    INSIGHT          = "insight"


# ── Sub-response models ───────────────────────────────────────────────────────

class WeeklyPoint(BaseModel):
    date: str
    score: float
    minutes: int


class HeatmapCell(BaseModel):
    date: str
    intensity: int   # 0-6
    minutes: int


class SubjectProgressItem(BaseModel):
    subject: str
    mastery_pct: float
    time_spent_minutes: int
    topics_total: int
    topics_mastered: int


class TopicItem(BaseModel):
    topic_id: str
    topic_name: str
    subject: str
    mastery_pct: float
    status: str
    time_spent_minutes: int


class NotificationItem(BaseModel):
    id: str
    notification_type: str
    title: str
    message: str
    is_read: bool
    icon: Optional[str] = None
    created_at: str


class ActivityItem(BaseModel):
    id: str
    subject: str
    topic_id: str
    topic_name: str
    mastery_pct: float
    time_spent_minutes: int
    status: str
    created_at: str


class QuickStats(BaseModel):
    current_streak: int
    longest_streak: int
    total_points: int
    ranking: int
    focus_score: float


# ── Top-level response models ─────────────────────────────────────────────────

class DashboardOverviewResponse(BaseModel):
    # Welcome card
    current_class: str
    section: str
    current_topic: str
    current_subject: str

    # Weekly progress
    weekly_data: List[WeeklyPoint]
    syllabus_completion_pct: float

    # Quick stats
    quick_stats: QuickStats

    # Notifications
    notifications: List[NotificationItem]
    unread_count: int

    # Subject progress
    subject_progress: List[SubjectProgressItem]

    # Strengths / weaknesses (top 3 each)
    strengths: List[TopicItem]
    weaknesses: List[TopicItem]

    # Recent activities
    recent_activities: List[ActivityItem]


class HeatmapResponse(BaseModel):
    year: int
    cells: List[HeatmapCell]


class SubjectProgressResponse(BaseModel):
    subjects: List[SubjectProgressItem]


class TopicAnalysisResponse(BaseModel):
    strengths: List[TopicItem]
    weaknesses: List[TopicItem]
    insufficient_data: List[TopicItem]


class RecentActivityResponse(BaseModel):
    activities: List[ActivityItem]
    total: int


class QuickStatsResponse(BaseModel):
    stats: QuickStats


class NotificationReadResponse(BaseModel):
    notification_id: str
    unread_count: int


# ── Request models ────────────────────────────────────────────────────────────

class StudySessionRequest(BaseModel):
    subject: str = Field(..., description="e.g. Physics, Chemistry, Math, Biology")
    topic: str   = Field(..., description="topic_id string, e.g. mechanics_and_thermodynamics")
    time_spent: int   = Field(..., ge=1, description="Minutes spent studying")
    mastery_achieved: float = Field(..., ge=0, le=100, description="Mastery percentage achieved")


class StudySessionResponse(BaseModel):
    message: str
    updated_stats: QuickStats
    heatmap_cell: Optional[HeatmapCell] = None
    new_notifications: List[NotificationItem] = Field(default_factory=list)
