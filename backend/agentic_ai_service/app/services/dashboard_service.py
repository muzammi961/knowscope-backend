# app/services/dashboard_service.py
"""
Dashboard service layer.
All methods are async and use Motor (MongoDB async driver).
In-process TTL cache avoids redundant DB reads for hot endpoints.
"""

from __future__ import annotations

import asyncio
import logging
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from bson import ObjectId
from app.core.database import db

logger = logging.getLogger(__name__)

# ── Collections ───────────────────────────────────────────────────────────────

user_progress_col       = db["user_progress"]
subject_progress_col    = db["subject_progress"]
topic_mastery_col       = db["topic_mastery"]
activity_heatmap_col    = db["activity_heatmap"]
notifications_col       = db["dashboard_notifications"]
learning_activity_col   = db["learning_activities"]


# ── In-process TTL cache ──────────────────────────────────────────────────────

_cache: Dict[str, Dict] = {}    # key → {data, expires_at}

def _cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry and time.time() < entry["expires_at"]:
        return entry["data"]
    return None

def _cache_set(key: str, data: Any, ttl_seconds: int = 300) -> None:
    _cache[key] = {"data": data, "expires_at": time.time() + ttl_seconds}

def _cache_invalidate(pattern: str) -> None:
    """Remove all keys that start with pattern."""
    for k in list(_cache.keys()):
        if k.startswith(pattern):
            del _cache[k]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _oid(doc: dict) -> dict:
    """Convert MongoDB _id ObjectId to string id field."""
    if doc and "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


def _mastery_status(pct: float) -> str:
    if pct >= 80:
        return "Mastered"
    elif pct >= 50:
        return "In Progress"
    elif pct > 0:
        return "Struggling"
    return "Not Started"


def _intensity(minutes: int) -> int:
    """Map study minutes to heatmap intensity 0-6."""
    if minutes == 0:   return 0
    if minutes < 15:   return 1
    if minutes < 30:   return 2
    if minutes < 60:   return 3
    if minutes < 90:   return 4
    if minutes < 120:  return 5
    return 6


def _fmt_notification(doc: dict) -> dict:
    doc = _oid(doc)
    doc["created_at"] = doc.get("created_at", datetime.utcnow()).isoformat() \
        if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at", ""))
    return doc


def _fmt_activity(doc: dict) -> dict:
    doc = _oid(doc)
    doc["created_at"] = doc.get("created_at", datetime.utcnow()).isoformat() \
        if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at", ""))
    return doc


# ── Core service functions ────────────────────────────────────────────────────

async def get_dashboard_overview(user_id: str) -> Dict:
    """Full dashboard overview with 5-minute TTL cache."""
    cache_key = f"overview:{user_id}"
    cached = _cache_get(cache_key)
    if cached:
        logger.debug("Cache hit: %s", cache_key)
        return cached

    # Ensure user has data (seed if first visit)
    from app.utils.dashboard_init import initialize_user_dashboard
    await initialize_user_dashboard(user_id)

    # Fetch user progress
    up = await user_progress_col.find_one({"user_id": user_id}) or {}

    # Fetch last 5 notifications
    notif_cursor = notifications_col.find(
        {"user_id": user_id}
    ).sort("created_at", -1).limit(5)
    notifications = [_fmt_notification(n) async for n in notif_cursor]
    unread_count = await notifications_col.count_documents(
        {"user_id": user_id, "is_read": False}
    )

    # Fetch subject progress
    subj_cursor = subject_progress_col.find({"user_id": user_id})
    subjects = []
    async for s in subj_cursor:
        subjects.append({
            "subject": s["subject"],
            "mastery_pct": round(s.get("mastery_pct", 0), 1),
            "time_spent_minutes": s.get("time_spent_minutes", 0),
            "topics_total": s.get("topics_total", 0),
            "topics_mastered": s.get("topics_mastered", 0),
        })

    # Strengths / weaknesses
    analysis = await get_topic_analysis(user_id)

    # Recent activities
    act_cursor = learning_activity_col.find(
        {"user_id": user_id}
    ).sort("created_at", -1).limit(10)
    activities = [_fmt_activity(a) async for a in act_cursor]

    # Weekly data
    weekly_raw = up.get("weekly_data", [])
    weekly = []
    for w in weekly_raw:
        weekly.append({
            "date": w.get("date", ""),
            "score": round(w.get("score", 0), 1),
            "minutes": w.get("minutes", 0),
        })

    result = {
        # Welcome card
        "current_class":   up.get("current_class", "Class 11"),
        "section":         up.get("section", "A"),
        "current_topic":   up.get("current_topic", "Not Set"),
        "current_subject": up.get("current_subject", "Physics"),

        # Weekly progress
        "weekly_data":              weekly,
        "syllabus_completion_pct":  round(up.get("syllabus_completion_pct", 0), 1),

        # Quick stats
        "quick_stats": {
            "current_streak": up.get("current_streak", 0),
            "longest_streak": up.get("longest_streak", 0),
            "total_points":   up.get("total_points", 0),
            "ranking":        up.get("ranking", 9999),
            "focus_score":    round(up.get("focus_score", 0), 1),
        },

        # Notifications
        "notifications": notifications,
        "unread_count":  unread_count,

        # Subject progress
        "subject_progress": subjects,

        # Strengths / weaknesses
        "strengths":   analysis["strengths"][:3],
        "weaknesses":  analysis["weaknesses"][:3],

        # Recent activities
        "recent_activities": activities,
    }

    _cache_set(cache_key, result, ttl_seconds=300)
    return result


async def get_heatmap_data(user_id: str, year: int) -> Dict:
    """52-week heatmap with 1-hour TTL cache."""
    cache_key = f"heatmap:{user_id}:{year}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    doc = await activity_heatmap_col.find_one({"user_id": user_id, "year": year})
    if not doc:
        # Return empty grid for the year
        cells = _empty_year_cells(year)
    else:
        cells = doc.get("cells", [])

    result = {"year": year, "cells": cells}
    _cache_set(cache_key, result, ttl_seconds=3600)
    return result


def _empty_year_cells(year: int) -> List[dict]:
    cells = []
    start = datetime(year, 1, 1)
    for i in range(365):
        d = start + timedelta(days=i)
        cells.append({"date": d.strftime("%Y-%m-%d"), "intensity": 0, "minutes": 0})
    return cells


async def get_subject_progress(user_id: str) -> List[Dict]:
    cache_key = f"subj:{user_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    cursor = subject_progress_col.find({"user_id": user_id})
    subjects = []
    async for s in cursor:
        subjects.append({
            "subject":           s["subject"],
            "mastery_pct":       round(s.get("mastery_pct", 0), 1),
            "time_spent_minutes": s.get("time_spent_minutes", 0),
            "topics_total":      s.get("topics_total", 0),
            "topics_mastered":   s.get("topics_mastered", 0),
        })

    _cache_set(cache_key, subjects, ttl_seconds=120)
    return subjects


async def get_topic_analysis(user_id: str) -> Dict:
    cache_key = f"topics:{user_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    cursor = topic_mastery_col.find({"user_id": user_id})
    strengths, weaknesses, insufficient = [], [], []

    async for t in cursor:
        mastery = t.get("mastery_pct", 0.0)
        item = {
            "topic_id":            t.get("topic_id", ""),
            "topic_name":          t.get("topic_name", ""),
            "subject":             t.get("subject", ""),
            "mastery_pct":         round(mastery, 1),
            "status":              _mastery_status(mastery),
            "time_spent_minutes":  t.get("time_spent_minutes", 0),
        }
        sessions = t.get("sessions_count", 0)
        if sessions == 0:
            insufficient.append(item)
        elif mastery >= 80:
            strengths.append(item)
        elif mastery < 50:
            weaknesses.append(item)
        else:
            insufficient.append(item)  # in-progress, not squarely strength/weakness

    strengths.sort(key=lambda x: -x["mastery_pct"])
    weaknesses.sort(key=lambda x: x["mastery_pct"])

    result = {
        "strengths":        strengths,
        "weaknesses":       weaknesses,
        "insufficient_data": insufficient,
    }
    _cache_set(cache_key, result, ttl_seconds=120)
    return result


async def get_recent_activities(user_id: str, limit: int = 10) -> Dict:
    cursor = learning_activity_col.find(
        {"user_id": user_id}
    ).sort("created_at", -1).limit(limit)
    activities = [_fmt_activity(a) async for a in cursor]
    return {"activities": activities, "total": len(activities)}


async def get_quick_stats(user_id: str) -> Dict:
    cache_key = f"stats:{user_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    up = await user_progress_col.find_one({"user_id": user_id}) or {}
    stats = {
        "current_streak": up.get("current_streak", 0),
        "longest_streak": up.get("longest_streak", 0),
        "total_points":   up.get("total_points", 0),
        "ranking":        up.get("ranking", 9999),
        "focus_score":    round(up.get("focus_score", 0), 1),
    }
    _cache_set(cache_key, stats, ttl_seconds=60)
    return stats


async def update_study_progress(
    user_id: str,
    subject: str,
    topic: str,
    time_spent: int,
    mastery_achieved: float,
) -> Dict:
    """
    Record a completed study session.
    Updates: subject_progress, topic_mastery, activity_heatmap, user_progress.
    Invalidates all caches for the user.
    """
    now = datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")
    year = now.year

    # 1. Topic mastery upsert
    existing_topic = await topic_mastery_col.find_one({"user_id": user_id, "topic_id": topic})
    if existing_topic:
        # Weighted average: give 30% weight to new session
        old_mastery = existing_topic.get("mastery_pct", 0)
        new_mastery = round(old_mastery * 0.7 + mastery_achieved * 0.3, 2)
        await topic_mastery_col.update_one(
            {"user_id": user_id, "topic_id": topic},
            {"$set": {
                "mastery_pct":         new_mastery,
                "status":              _mastery_status(new_mastery),
                "last_studied_at":     now,
                "updated_at":          now,
            }, "$inc": {
                "time_spent_minutes":  time_spent,
                "sessions_count":      1,
            }}
        )
        final_mastery = new_mastery
    else:
        final_mastery = round(mastery_achieved, 2)
        await topic_mastery_col.insert_one({
            "user_id":             user_id,
            "topic_id":            topic,
            "topic_name":          topic.replace("_", " ").title(),
            "subject":             subject,
            "mastery_pct":         final_mastery,
            "status":              _mastery_status(final_mastery),
            "time_spent_minutes":  time_spent,
            "sessions_count":      1,
            "last_studied_at":     now,
            "created_at":          now,
            "updated_at":          now,
        })

    # 2. Subject progress upsert
    subj_doc = await subject_progress_col.find_one({"user_id": user_id, "subject": subject})
    if subj_doc:
        # Recalculate average mastery from all topics in that subject
        topic_docs = topic_mastery_col.find({"user_id": user_id, "subject": subject})
        masteries = [t["mastery_pct"] async for t in topic_docs]
        avg_mastery = round(sum(masteries) / len(masteries), 2) if masteries else 0
        mastered_count = sum(1 for m in masteries if m >= 80)

        await subject_progress_col.update_one(
            {"user_id": user_id, "subject": subject},
            {"$set": {
                "mastery_pct":     avg_mastery,
                "topics_mastered": mastered_count,
                "topics_total":    len(masteries),
                "last_studied_at": now,
                "updated_at":      now,
            }, "$inc": {
                "time_spent_minutes": time_spent,
            }}
        )
    else:
        await subject_progress_col.insert_one({
            "user_id":             user_id,
            "subject":             subject,
            "mastery_pct":         final_mastery,
            "time_spent_minutes":  time_spent,
            "topics_total":        1,
            "topics_mastered":     1 if final_mastery >= 80 else 0,
            "last_studied_at":     now,
            "created_at":          now,
            "updated_at":          now,
        })

    # 3. Learning activity log
    await learning_activity_col.insert_one({
        "user_id":             user_id,
        "subject":             subject,
        "topic_id":            topic,
        "topic_name":          topic.replace("_", " ").title(),
        "mastery_pct":         final_mastery,
        "time_spent_minutes":  time_spent,
        "status":              _mastery_status(final_mastery),
        "created_at":          now,
        "updated_at":          now,
    })

    # 4. Heatmap update
    intensity = _intensity(time_spent)
    heatmap_doc = await activity_heatmap_col.find_one({"user_id": user_id, "year": year})
    if heatmap_doc:
        cells = heatmap_doc.get("cells", [])
        updated = False
        for cell in cells:
            if cell["date"] == today_str:
                cell["minutes"] += time_spent
                cell["intensity"] = _intensity(cell["minutes"])
                updated = True
                break
        if not updated:
            cells.append({"date": today_str, "intensity": intensity, "minutes": time_spent})
        await activity_heatmap_col.update_one(
            {"user_id": user_id, "year": year},
            {"$set": {"cells": cells, "updated_at": now}}
        )
        today_cell = next((c for c in cells if c["date"] == today_str), None)
    else:
        cells = _empty_year_cells(year)
        for cell in cells:
            if cell["date"] == today_str:
                cell["minutes"] = time_spent
                cell["intensity"] = intensity
        await activity_heatmap_col.insert_one({
            "user_id":    user_id,
            "year":       year,
            "cells":      cells,
            "created_at": now,
            "updated_at": now,
        })
        today_cell = {"date": today_str, "intensity": intensity, "minutes": time_spent}

    # 5. User progress: points, streak, focus score
    up = await user_progress_col.find_one({"user_id": user_id}) or {}
    points_earned = int(time_spent * 2 + final_mastery * 0.5)
    new_total_points = up.get("total_points", 0) + points_earned

    # Streak logic
    last_streak_date = up.get("last_streak_date", "")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    current_streak = up.get("current_streak", 0)
    if last_streak_date == yesterday:
        current_streak += 1
    elif last_streak_date != today_str:
        current_streak = 1
    longest_streak = max(up.get("longest_streak", 0), current_streak)

    # Focus score: weighted combo
    focus_score = round(
        min(100, final_mastery * 0.4 + min(time_spent / 120 * 100, 100) * 0.3 + current_streak * 2),
        1
    )

    await user_progress_col.update_one(
        {"user_id": user_id},
        {"$set": {
            "total_points":       new_total_points,
            "current_streak":     current_streak,
            "longest_streak":     longest_streak,
            "focus_score":        focus_score,
            "current_topic":      topic.replace("_", " ").title(),
            "current_subject":    subject,
            "last_streak_date":   today_str,
            "updated_at":         now,
        }},
        upsert=True,
    )

    # 6. Recalculate syllabus completion
    all_subj = subject_progress_col.find({"user_id": user_id})
    pcts = [s["mastery_pct"] async for s in all_subj]
    syllabus_pct = round(sum(pcts) / len(pcts), 1) if pcts else 0
    await user_progress_col.update_one(
        {"user_id": user_id},
        {"$set": {"syllabus_completion_pct": syllabus_pct}}
    )

    # Invalidate all user caches
    _cache_invalidate(f"overview:{user_id}")
    _cache_invalidate(f"heatmap:{user_id}")
    _cache_invalidate(f"subj:{user_id}")
    _cache_invalidate(f"topics:{user_id}")
    _cache_invalidate(f"stats:{user_id}")

    # 7. Generate notifications if milestones hit
    new_notifications = await generate_ai_notifications(user_id, trigger={
        "mastery": final_mastery,
        "topic": topic,
        "subject": subject,
        "streak": current_streak,
    })

    stats = {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_points":   new_total_points,
        "ranking":        up.get("ranking", 9999),
        "focus_score":    focus_score,
    }
    return {
        "stats": stats,
        "heatmap_cell": today_cell,
        "new_notifications": [_fmt_notification(n) for n in new_notifications],
    }


async def generate_ai_notifications(user_id: str, trigger: Optional[Dict] = None) -> List[Dict]:
    """
    Pattern-based notification generation (no LLM call).
    Creates notifications based on study milestones and patterns.
    """
    now = datetime.utcnow()
    created = []

    if trigger:
        mastery = trigger.get("mastery", 0)
        topic   = trigger.get("topic", "")
        subject = trigger.get("subject", "")
        streak  = trigger.get("streak", 0)

        notifications_to_create = []

        if mastery >= 85:
            notifications_to_create.append({
                "user_id":           user_id,
                "notification_type": "insight",
                "title":             "🏆 Mastery Achieved!",
                "message":           f"Excellent! You've mastered {topic.replace('_',' ').title()} with {mastery:.0f}% proficiency.",
                "is_read":           False,
                "icon":              "trophy",
                "created_at":        now,
                "updated_at":        now,
            })
        elif mastery < 40:
            notifications_to_create.append({
                "user_id":           user_id,
                "notification_type": "resource",
                "title":             "📚 Need More Practice",
                "message":           f"Your mastery in {topic.replace('_',' ').title()} is at {mastery:.0f}%. Try reviewing the foundational concepts.",
                "is_read":           False,
                "icon":              "book",
                "created_at":        now,
                "updated_at":        now,
            })

        if streak > 0 and streak % 7 == 0:
            notifications_to_create.append({
                "user_id":           user_id,
                "notification_type": "insight",
                "title":             f"🔥 {streak}-Day Streak!",
                "message":           f"You've been studying for {streak} consecutive days. Keep the momentum!",
                "is_read":           False,
                "icon":              "fire",
                "created_at":        now,
                "updated_at":        now,
            })

        for n in notifications_to_create:
            result = await notifications_col.insert_one(n)
            n["_id"] = result.inserted_id
            created.append(n)

    return created


async def mark_notification_read(user_id: str, notification_id: str) -> int:
    """Mark a notification as read and return updated unread count."""
    try:
        oid = ObjectId(notification_id)
    except Exception:
        return -1

    await notifications_col.update_one(
        {"_id": oid, "user_id": user_id},
        {"$set": {"is_read": True, "updated_at": datetime.utcnow()}}
    )
    unread = await notifications_col.count_documents({"user_id": user_id, "is_read": False})
    # Invalidate overview cache since unread count changed
    _cache_invalidate(f"overview:{user_id}")
    return unread
