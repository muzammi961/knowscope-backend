# app/services/dashboard_service.py
"""
Dashboard service layer — all business logic and MongoDB aggregation pipelines.
Collections used:
  - quiz_attempts_col   : per-quiz scores
  - study_sessions_col  : study session logs
  - mastery_scores_col  : topic mastery levels
  - user_stats_col      : aggregated user statistics (streaks, points, rank)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from bson import ObjectId

from app.core.database import (
    quiz_attempts_col,
    study_sessions_col,
    mastery_scores_col,
    user_stats_col,
)

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

SHADE_MAP = {
    0: "bg-gray-100",
    1: "bg-gray-200",
    2: "bg-gray-300",
    3: "bg-gray-400",
    4: "bg-gray-500",
    5: "bg-gray-600",
    6: "bg-black",
}

TRACKED_SUBJECTS = ["Physics", "Chemistry", "Math", "Biology"]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _score_to_mastery(score: float) -> int:
    """Map quiz score percentage to mastery level 0-4."""
    if score >= 90: return 4
    if score >= 75: return 3
    if score >= 60: return 2
    if score >= 40: return 1
    return 0


def _mastery_to_heatmap(mastery: float) -> int:
    """Map average mastery (0-4) to heatmap intensity (0-6)."""
    if mastery == 0:   return 0
    if mastery < 0.5:  return 1
    if mastery < 1.5:  return 2
    if mastery < 2.5:  return 3
    if mastery < 3.5:  return 4
    if mastery < 4.0:  return 5
    return 6


def _fmt_dt(dt: datetime) -> str:
    return dt.isoformat() if isinstance(dt, datetime) else str(dt)


# ── User Stats ──────────────────────────────────────────────────────────────────

async def get_or_create_user_stats(user_id: str) -> dict:
    """Fetch user stats document, creating default if missing."""
    doc = await user_stats_col.find_one({"user_id": user_id})
    if not doc:
        default = {
            "user_id":        user_id,
            "current_streak": 0,
            "longest_streak": 0,
            "total_points":   0,
            "rank":           9999,
            "focus_score":    0.0,
            "last_active":    None,
            "created_at":     datetime.utcnow(),
            "updated_at":     datetime.utcnow(),
        }
        await user_stats_col.insert_one(default)
        return default
    return doc


async def _update_streak_and_points(user_id: str, points_earned: int) -> dict:
    """
    Update streak logic: if user was active yesterday → extend streak,
    if today already → keep, otherwise reset to 1.
    """
    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    doc = await get_or_create_user_stats(user_id)
    last_active = doc.get("last_active")
    last_active_str = last_active.strftime("%Y-%m-%d") if isinstance(last_active, datetime) else str(last_active or "")

    current_streak = doc.get("current_streak", 0)
    if last_active_str == today:
        # Already updated today — just add points
        pass
    elif last_active_str == yesterday:
        current_streak += 1
    else:
        current_streak = 1

    longest_streak = max(doc.get("longest_streak", 0), current_streak)
    new_points = doc.get("total_points", 0) + points_earned

    # Simple focus score: weighted recent activity
    focus_score = round(min(100.0, current_streak * 5 + points_earned * 0.1), 1)

    await user_stats_col.update_one(
        {"user_id": user_id},
        {"$set": {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_points":   new_points,
            "focus_score":    focus_score,
            "last_active":    now,
            "updated_at":     now,
        }},
        upsert=True,
    )
    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_points":   new_points,
        "rank":           doc.get("rank", 9999),
        "focus_score":    focus_score,
    }


# ── Study Session ──────────────────────────────────────────────────────────────

async def log_study_session(user_id: str, subject: str, duration_minutes: int, topics_covered: List[str]) -> str:
    """Insert a study session document and update streak/points."""
    now = datetime.utcnow()
    doc = {
        "user_id":          user_id,
        "subject":          subject,
        "duration_minutes": duration_minutes,
        "topics_covered":   topics_covered,
        "timestamp":        now,
    }
    result = await study_sessions_col.insert_one(doc)
    points = duration_minutes * 1  # 1 pt per minute
    await _update_streak_and_points(user_id, points)
    return str(result.inserted_id)


# ── Quiz Attempt ───────────────────────────────────────────────────────────────

async def record_quiz_attempt(
    user_id: str,
    quiz_id: str,
    subject: str,
    class_level: str,
    topic: str,
    difficulty: str,
    score_percentage: float,
    questions_answered: int,
) -> Dict:
    """
    Store a QuizAttempt document, upsert mastery score, update user stats.
    Returns mastery_level and points_earned.
    """
    now = datetime.utcnow()
    mastery_level = _score_to_mastery(score_percentage)
    points = int(score_percentage * 0.5 * questions_answered)

    # 1. Insert quiz attempt
    await quiz_attempts_col.insert_one({
        "user_id":            user_id,
        "quiz_id":            quiz_id,
        "subject":            subject,
        "class_level":        class_level,
        "topic":              topic,
        "difficulty":         difficulty,
        "score_percentage":   round(score_percentage, 2),
        "questions_answered": questions_answered,
        "mastery_level":      mastery_level,
        "date":               now,
    })

    # 2. Upsert mastery score (weighted rolling average)
    existing = await mastery_scores_col.find_one({"user_id": user_id, "subject": subject, "topic": topic})
    if existing:
        old = existing.get("mastery_level", 0)
        new_mastery = round(old * 0.6 + mastery_level * 0.4)
        await mastery_scores_col.update_one(
            {"user_id": user_id, "subject": subject, "topic": topic},
            {"$set": {
                "mastery_level":  new_mastery,
                "last_practiced": now,
                "updated_at":     now,
            }, "$inc": {"attempt_count": 1}}
        )
        mastery_level = new_mastery
    else:
        await mastery_scores_col.insert_one({
            "user_id":       user_id,
            "subject":       subject,
            "topic":         topic,
            "mastery_level": mastery_level,
            "last_practiced": now,
            "attempt_count": 1,
            "created_at":    now,
            "updated_at":    now,
        })

    # 3. Update user stats
    stats = await _update_streak_and_points(user_id, points)

    return {
        "mastery_level": mastery_level,
        "points_earned": points,
        "streak": stats["current_streak"],
    }


# ── Dashboard: Overview ────────────────────────────────────────────────────────

async def get_overview(user_id: str) -> Dict:
    doc = await get_or_create_user_stats(user_id)
    return {
        "user_stats": {
            "current_streak": doc.get("current_streak", 0),
            "longest_streak": doc.get("longest_streak", 0),
            "total_points":   doc.get("total_points", 0),
            "rank":           doc.get("rank", 9999),
            "focus_score":    round(doc.get("focus_score", 0.0), 1),
        }
    }


# ── Dashboard: Heatmap ─────────────────────────────────────────────────────────

async def get_mastery_heatmap(user_id: str) -> Dict:
    """
    Build 52-week × 7-day heatmap from quiz_attempts.
    One cell per calendar day; mastery_level = avg score converted to 0-6 scale.
    """
    now = datetime.utcnow()
    start = now - timedelta(weeks=52)

    # Aggregation: group quiz attempts by date, avg mastery_level
    pipeline = [
        {"$match": {
            "user_id": user_id,
            "date": {"$gte": start},
        }},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$date"}},
            "avg_mastery": {"$avg": "$mastery_level"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]

    cursor = quiz_attempts_col.aggregate(pipeline)
    by_date: Dict[str, float] = {}
    async for row in cursor:
        by_date[row["_id"]] = row["avg_mastery"]

    # Also include study sessions (treat any session as low activity if no quiz)
    sess_pipeline = [
        {"$match": {"user_id": user_id, "timestamp": {"$gte": start}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
        }},
    ]
    sess_cursor = study_sessions_col.aggregate(sess_pipeline)
    study_days = set()
    async for row in sess_cursor:
        study_days.add(row["_id"])

    # Build ordered cell list for 364 days (52 weeks)
    cells = []
    month_labels: List[Dict[str, Any]] = []
    last_month = None
    col_index = 0

    for i in range(364):
        day = start + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")

        # Month label tracking
        month_name = day.strftime("%b")
        if month_name != last_month:
            month_labels.append({"month": month_name, "col_index": col_index})
            last_month = month_name
        if day.weekday() == 6:   # Sunday = new column
            col_index += 1

        if date_str in by_date:
            intensity = _mastery_to_heatmap(by_date[date_str])
        elif date_str in study_days:
            intensity = 1          # studied but no quiz
        else:
            intensity = 0

        cells.append({
            "date":          date_str,
            "mastery_level": intensity,
            "shade":         SHADE_MAP.get(intensity, "bg-gray-100"),
        })

    return {"cells": cells, "month_labels": month_labels}


# ── Dashboard: Subject Progress ────────────────────────────────────────────────

async def get_subject_progress(user_id: str) -> List[Dict]:
    """
    For each tracked subject, average score_percentage from the last 10 attempts.
    Returns percentage 0-100.
    """
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": "$subject",
            "avg_score": {"$avg": "$score_percentage"},
            "count": {"$sum": 1},
        }},
    ]
    cursor = quiz_attempts_col.aggregate(pipeline)
    by_subject: Dict[str, float] = {}
    async for row in cursor:
        by_subject[row["_id"]] = round(row["avg_score"], 1)

    results = []
    for subj in TRACKED_SUBJECTS:
        results.append({
            "subject":    subj,
            "percentage": by_subject.get(subj, 0.0),
        })
    return results


# ── Dashboard: Topic Analysis ──────────────────────────────────────────────────

async def get_topic_analysis(user_id: str) -> Dict:
    """
    strengths : mastery_level >= 4
    weaknesses: mastery_level <= 2  (or no data)
    """
    cursor = mastery_scores_col.find({"user_id": user_id})
    strengths = []
    weaknesses = []

    async for doc in cursor:
        mastery = doc.get("mastery_level", 0)
        topic   = doc.get("topic", "")
        item = {"topic": topic, "mastery_level": mastery}

        if mastery >= 4:
            strengths.append(item)
        elif mastery <= 2:
            weaknesses.append({**item, "has_data": True})

    # Sort for relevance
    strengths.sort(key=lambda x: -x["mastery_level"])
    weaknesses.sort(key=lambda x: x["mastery_level"])

    return {"strengths": strengths, "weaknesses": weaknesses}


# ── Dashboard: Activity Feed ───────────────────────────────────────────────────

async def get_activity_feed(user_id: str, limit: int = 20) -> List[Dict]:
    """
    Merge recent quiz attempts and study sessions, sorted newest-first.
    """
    activities: List[Dict] = []

    # Quiz attempts
    qa_cursor = quiz_attempts_col.find({"user_id": user_id}).sort("date", -1).limit(limit)
    async for q in qa_cursor:
        activities.append({
            "activity_type":    "quiz",
            "subject":          q.get("subject", ""),
            "topic":            q.get("topic", ""),
            "score_percentage": q.get("score_percentage"),
            "duration_minutes": None,
            "timestamp":        _fmt_dt(q.get("date", datetime.utcnow())),
        })

    # Study sessions
    ss_cursor = study_sessions_col.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
    async for s in ss_cursor:
        activities.append({
            "activity_type":    "study",
            "subject":          s.get("subject", ""),
            "topic":            ", ".join(s.get("topics_covered", [])),
            "score_percentage": None,
            "duration_minutes": s.get("duration_minutes"),
            "timestamp":        _fmt_dt(s.get("timestamp", datetime.utcnow())),
        })

    # Merge and sort by timestamp desc, take top `limit`
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return activities[:limit]
