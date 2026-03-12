# app/core/database.py
"""
Central MongoDB connection and collection registry.
All collections are defined here; import from this module everywhere.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client[settings.DATABASE_NAME]

# ── Existing collections ──────────────────────────────────────────────────────
quizzes_collection     = db["quizzes"]
evaluations_collection = db["evaluations"]
students_collection    = db["students"]

# ── Dashboard / learning collections ─────────────────────────────────────────
study_sessions_col  = db["study_sessions"]    # StudySession documents
quiz_attempts_col   = db["quiz_attempts"]     # QuizAttempt documents
mastery_scores_col  = db["mastery_scores"]    # MasteryScore documents
user_stats_col      = db["user_stats"]        # UserStats documents (one per user)