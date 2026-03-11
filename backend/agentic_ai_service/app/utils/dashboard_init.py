# app/utils/dashboard_init.py
"""
Mock data initializer for the student dashboard.
Called on first dashboard load for a new user.
Seeds all 6 MongoDB collections with realistic data.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import db

logger = logging.getLogger(__name__)

# ── Collections ───────────────────────────────────────────────────────────────

user_progress_col     = db["user_progress"]
subject_progress_col  = db["subject_progress"]
topic_mastery_col     = db["topic_mastery"]
activity_heatmap_col  = db["activity_heatmap"]
notifications_col     = db["dashboard_notifications"]
learning_activity_col = db["learning_activities"]


# ── Curriculum data ───────────────────────────────────────────────────────────

SUBJECTS_TOPICS = {
    "Physics": [
        ("mechanics_and_thermodynamics", "Mechanics & Thermodynamics"),
        ("electrostatics_and_optics_and_modern_physics", "Electrostatics, Optics & Modern Physics"),
        ("waves_and_oscillations", "Waves & Oscillations"),
    ],
    "Chemistry": [
        ("atomic_structure_and_chemical_bonding", "Atomic Structure & Chemical Bonding"),
        ("electrochemistry_and_organic_chemistry", "Electrochemistry & Organic Chemistry"),
        ("thermodynamics_chemistry", "Chemical Thermodynamics"),
    ],
    "Mathematics": [
        ("calculus_and_linear_programming", "Calculus & Linear Programming"),
        ("sets_relations_and_functions", "Sets, Relations & Functions"),
        ("quadratic_equations_and_trigonometry", "Quadratic Equations & Trigonometry"),
    ],
    "Biology": [
        ("cell_biology_and_plant_physiology", "Cell Biology & Plant Physiology"),
        ("genetics_and_evolution_and_ecology", "Genetics, Evolution & Ecology"),
        ("human_physiology", "Human Physiology"),
    ],
}

NOTIFICATION_TEMPLATES = [
    {
        "notification_type": "exam",
        "title": "📅 Board Exam Reminder",
        "message": "Physics board exam is in 45 days. Review all chapters systematically.",
        "icon": "calendar",
    },
    {
        "notification_type": "insight",
        "title": "📈 Study Insight",
        "message": "Your Chemistry mastery is improving! You're in the top 15% of your class.",
        "icon": "chart",
    },
    {
        "notification_type": "resource",
        "title": "📚 Recommended Resource",
        "message": "A new practice set for Electrostatics is available. 20 questions, 30 min.",
        "icon": "book",
    },
    {
        "notification_type": "doubt_resolution",
        "title": "✅ Doubt Resolved",
        "message": "Your query on integration by parts has been answered. Check the solution.",
        "icon": "check",
    },
    {
        "notification_type": "insight",
        "title": "🔥 Streak Milestone",
        "message": "Amazing! You've studied for 7 consecutive days. Your focus score increased by 12 points!",
        "icon": "fire",
    },
]


def _intensity(minutes: int) -> int:
    if minutes == 0:  return 0
    if minutes < 15:  return 1
    if minutes < 30:  return 2
    if minutes < 60:  return 3
    if minutes < 90:  return 4
    if minutes < 120: return 5
    return 6


async def initialize_user_dashboard(user_id: str) -> bool:
    """
    Seed all dashboard collections for a new user.
    Returns True if data was created, False if user already has data.
    """
    existing = await user_progress_col.find_one({"user_id": user_id})
    if existing:
        return False

    logger.info("Initializing dashboard for user: %s", user_id)
    now = datetime.utcnow()

    # ── 1. User Progress ─────────────────────────────────────────────────────
    weekly_data = []
    base_score = random.uniform(45, 65)
    for i in range(6, -1, -1):
        d = now - timedelta(days=i)
        score = max(0, min(100, base_score + random.uniform(-10, 15)))
        minutes = random.randint(20, 120) if random.random() > 0.2 else 0
        weekly_data.append({
            "date":    d.strftime("%Y-%m-%d"),
            "score":   round(score, 1),
            "minutes": minutes,
        })
        base_score = score

    streak = random.randint(3, 14)
    points = random.randint(1200, 4500)

    await user_progress_col.insert_one({
        "user_id":                  user_id,
        "current_class":            "Class 12",
        "section":                  "A",
        "current_topic":            "Mechanics & Thermodynamics",
        "current_subject":          "Physics",
        "total_points":             points,
        "ranking":                  random.randint(50, 300),
        "current_streak":           streak,
        "longest_streak":           streak + random.randint(0, 7),
        "focus_score":              round(random.uniform(55, 85), 1),
        "syllabus_completion_pct":  round(random.uniform(30, 65), 1),
        "weekly_data":              weekly_data,
        "last_streak_date":         now.strftime("%Y-%m-%d"),
        "created_at":               now,
        "updated_at":               now,
    })

    # ── 2. Subject Progress ──────────────────────────────────────────────────
    for subject, topics in SUBJECTS_TOPICS.items():
        mastery = round(random.uniform(30, 80), 1)
        mastered = sum(1 for _ in topics if random.random() > 0.5)
        await subject_progress_col.insert_one({
            "user_id":             user_id,
            "subject":             subject,
            "mastery_pct":         mastery,
            "time_spent_minutes":  random.randint(120, 600),
            "topics_total":        len(topics),
            "topics_mastered":     mastered,
            "last_studied_at":     now - timedelta(hours=random.randint(1, 48)),
            "created_at":          now,
            "updated_at":          now,
        })

    # ── 3. Topic Mastery ─────────────────────────────────────────────────────
    def mastery_status(pct):
        if pct >= 80: return "Mastered"
        if pct >= 50: return "In Progress"
        if pct > 0:   return "Struggling"
        return "Not Started"

    for subject, topics in SUBJECTS_TOPICS.items():
        for topic_id, topic_name in topics:
            mastery = round(random.uniform(15, 95), 1)
            await topic_mastery_col.insert_one({
                "user_id":             user_id,
                "topic_id":            topic_id,
                "topic_name":          topic_name,
                "subject":             subject,
                "mastery_pct":         mastery,
                "status":              mastery_status(mastery),
                "time_spent_minutes":  random.randint(30, 200),
                "sessions_count":      random.randint(1, 8),
                "last_studied_at":     now - timedelta(hours=random.randint(2, 72)),
                "created_at":          now,
                "updated_at":          now,
            })

    # ── 4. Activity Heatmap (52 weeks) ───────────────────────────────────────
    year = now.year
    cells = []
    start_of_year = datetime(year, 1, 1)
    for i in range(365):
        d = start_of_year + timedelta(days=i)
        future = d > now
        if future:
            minutes = 0
        else:
            # ~70% chance of studying on any past day
            minutes = random.randint(15, 150) if random.random() > 0.30 else 0
        cells.append({
            "date":      d.strftime("%Y-%m-%d"),
            "intensity": _intensity(minutes),
            "minutes":   minutes,
        })

    await activity_heatmap_col.insert_one({
        "user_id":    user_id,
        "year":       year,
        "cells":      cells,
        "created_at": now,
        "updated_at": now,
    })

    # ── 5. Notifications ─────────────────────────────────────────────────────
    for i, tmpl in enumerate(NOTIFICATION_TEMPLATES):
        time_offset = timedelta(hours=i * 6 + random.randint(0, 5))
        await notifications_col.insert_one({
            "user_id":           user_id,
            **tmpl,
            "is_read":           (i > 2),   # first 3 unread, rest read
            "created_at":        now - time_offset,
            "updated_at":        now - time_offset,
        })

    # ── 6. Learning Activities ───────────────────────────────────────────────
    all_topics = [
        (subject, topic_id, topic_name)
        for subject, topics in SUBJECTS_TOPICS.items()
        for topic_id, topic_name in topics
    ]
    random.shuffle(all_topics)

    for i, (subject, topic_id, topic_name) in enumerate(all_topics[:10]):
        mastery = round(random.uniform(20, 95), 1)
        time_offset = timedelta(days=i // 2, hours=random.randint(0, 12))
        await learning_activity_col.insert_one({
            "user_id":             user_id,
            "subject":             subject,
            "topic_id":            topic_id,
            "topic_name":          topic_name,
            "mastery_pct":         mastery,
            "time_spent_minutes":  random.randint(20, 90),
            "status":              mastery_status(mastery),
            "created_at":          now - time_offset,
            "updated_at":          now - time_offset,
        })

    logger.info("Dashboard initialized for user: %s", user_id)
    return True
