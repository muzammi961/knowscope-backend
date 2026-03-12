# app/routes/dashboard.py
"""
Dashboard API endpoints — all require JWT auth via Authorization header.
"""

from __future__ import annotations
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from jose import jwt, JWTError, ExpiredSignatureError
import os
from dotenv import load_dotenv
from app.services import dashboard_service
load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

# ── Shared auth dependency ────────────────────────────────────────────────────

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM  = os.getenv("JWT_ALGORITHM", "HS256")


def decode_access_token(token: str) -> dict:
    try:
        print("SECRET_KEY",SECRET_KEY)
        print("ALGORITHM",ALGORITHM)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        role    = payload.get("role")
        if not user_id or not role:
            raise JWTError("Invalid token payload")
        return {"user_id": str(user_id), "email": payload.get("email"), "role": role}
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user_from_header(authorization: str = Header(...)) -> dict:
    authorization = authorization.strip()
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header. Expected: Bearer <token>",
        )
    token = authorization.split(" ", 1)[1]
    return decode_access_token(token)

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/overview",
    summary="User stats overview (streaks, points, rank, focus_score)",
)
async def overview(current_user: dict = Depends(get_current_user_from_header)):
    """
    Returns aggregated user statistics from UserStats collection.
    - current_streak / longest_streak
    - total_points
    - rank
    - focus_score
    """
    try:
        data = await dashboard_service.get_overview(current_user["user_id"])
        return {"success": True, "data": data}
    except Exception as e:
        logger.exception("overview error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/mastery-heatmap",
    summary="52-week × 7-day mastery heatmap",
)
async def mastery_heatmap(current_user: dict = Depends(get_current_user_from_header)):
    """
    Returns 364 daily cells.
    Each cell: { date, mastery_level (0-6), shade (Tailwind class) }
    shade mapping:
      0 → bg-gray-100, 1 → bg-gray-200, 2 → bg-gray-300, 3 → bg-gray-400,
      4 → bg-gray-500, 5 → bg-gray-600, 6 → bg-black
    Also returns month_labels: [{month: "Jan", col_index: 0}, ...]
    """
    try:
        data = await dashboard_service.get_mastery_heatmap(current_user["user_id"])
        return {"success": True, "data": data}
    except Exception as e:
        logger.exception("heatmap error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/subject-progress",
    summary="Subject-wise average score percentages",
)
async def subject_progress(current_user: dict = Depends(get_current_user_from_header)):
    """
    Returns percentage for Physics, Chemistry, Math, Biology
    calculated from all quiz_attempts via MongoDB aggregation.
    """
    try:
        data = await dashboard_service.get_subject_progress(current_user["user_id"])
        return {"success": True, "data": {"subjects": data}}
    except Exception as e:
        logger.exception("subject_progress error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/topic-analysis",
    summary="Strengths and weaknesses by topic",
)
async def topic_analysis(current_user: dict = Depends(get_current_user_from_header)):
    """
    - strengths : topics with mastery_level >= 4
    - weaknesses: topics with mastery_level <= 2
    Topics with no data are excluded (frontend should show 'Not enough data').
    """
    try:
        data = await dashboard_service.get_topic_analysis(current_user["user_id"])
        return {"success": True, "data": data}
    except Exception as e:
        logger.exception("topic_analysis error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/activity-feed",
    summary="Recent quiz completions and study sessions",
)
async def activity_feed(
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user_from_header),
):
    """Returns merged recent activity list (quizzes + study sessions) newest-first."""
    try:
        activities = await dashboard_service.get_activity_feed(current_user["user_id"], limit=limit)
        return {"success": True, "data": {"activities": activities}}
    except Exception as e:
        logger.exception("activity_feed error")
        raise HTTPException(status_code=500, detail=str(e))
