# app/routes/dashboard.py
"""
FastAPI router for all dashboard endpoints.
All routes require JWT authentication via Authorization header.
"""

from __future__ import annotations
import logging
from typing import Optional
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.schemas.dashboard import (
    DashboardOverviewResponse,
    HeatmapResponse,
    SubjectProgressResponse,
    TopicAnalysisResponse,
    RecentActivityResponse,
    QuickStatsResponse,
    NotificationReadResponse,
    StudySessionRequest,
    StudySessionResponse,
    QuickStats,
    NotificationItem,
    HeatmapCell,
)
from app.services import dashboard_service
from app.ws.dashboard_ws import send_dashboard_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


# ── Auth dependency (shared with main.py) ─────────────────────────────────────

from jose import jwt, JWTError, ExpiredSignatureError
import os




load_dotenv()


SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM")




def decode_access_token(token: str):
    try:
        print("SECRET_KEY:", SECRET_KEY)
        print("ALGORITHM:", ALGORITHM)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        role = payload.get("role")
        if not user_id or not role:
            raise JWTError("Invalid token payload")
        return {"user_id": user_id,"email": payload.get("email"),"role": role}
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    
    
async def get_current_user_from_header(authorization: str = Header(...)):
    authorization = authorization.strip()  # remove trailing/leading spaces or newlines
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header. Expected: Bearer <token>"
        )
    token = authorization.split(" ", 1)[1]
    return decode_access_token(token)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get(
    "/overview",
    summary="Full dashboard overview",
    response_description="All dashboard data in one call",
)
async def get_overview(current_user: dict = Depends(get_current_user_from_header)):
    """
    Returns the complete student dashboard data including:
    - Welcome card (class, section, current topic)
    - Weekly progress line-graph data
    - AI notifications with unread count
    - Quick stats (streaks, points, ranking, focus score)
    - Subject completion percentages
    - Strengths and weaknesses
    - Recent learning activities
    """
    try:
        data = await dashboard_service.get_dashboard_overview(current_user["user_id"])
        return {"success": True, "data": data}
    except Exception as e:
        logger.exception("Error fetching dashboard overview")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/heatmap",
    summary="52-week activity heatmap",
)
async def get_heatmap(
    year: Optional[int] = Query(None, description="Year for heatmap (defaults to current year)"),
    current_user: dict = Depends(get_current_user_from_header),
):
    """
    Returns 52 weeks (≤ 365 days) of daily study activity.
    Each cell has: date, intensity (0-6), minutes.
    """
    import datetime
    if year is None:
        year = datetime.datetime.utcnow().year
    try:
        data = await dashboard_service.get_heatmap_data(current_user["user_id"], year)
        return {"success": True, "data": data}
    except Exception as e:
        logger.exception("Error fetching heatmap")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/subject-progress",
    summary="Subject-wise completion percentages",
)
async def get_subject_progress(current_user: dict = Depends(get_current_user_from_header)):
    """Returns mastery percentage and time spent per subject."""
    try:
        subjects = await dashboard_service.get_subject_progress(current_user["user_id"])
        return {"success": True, "data": {"subjects": subjects}}
    except Exception as e:
        logger.exception("Error fetching subject progress")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/topic-analysis",
    summary="Strengths and weaknesses by topic",
)
async def get_topic_analysis(current_user: dict = Depends(get_current_user_from_header)):
    """
    Analyzes all topic mastery records:
    - strengths: topics > 80% mastery
    - weaknesses: topics < 50% mastery
    - insufficient_data: topics with 0 sessions or 50-80% (in-progress)
    """
    try:
        data = await dashboard_service.get_topic_analysis(current_user["user_id"])
        return {"success": True, "data": data}
    except Exception as e:
        logger.exception("Error fetching topic analysis")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/recent-activity",
    summary="Recent learning activities",
)
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50, description="Number of activities to return"),
    current_user: dict = Depends(get_current_user_from_header),
):
    """Returns the most recent learning activities with mastery levels."""
    try:
        data = await dashboard_service.get_recent_activities(current_user["user_id"], limit=limit)
        return {"success": True, "data": data}
    except Exception as e:
        logger.exception("Error fetching recent activities")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/quick-stats",
    summary="Quick stats: streaks, points, ranking, focus score",
)
async def get_quick_stats(current_user: dict = Depends(get_current_user_from_header)):
    """Returns gamification stats: streak, points, ranking and focus score."""
    try:
        stats = await dashboard_service.get_quick_stats(current_user["user_id"])
        return {"success": True, "data": {"stats": stats}}
    except Exception as e:
        logger.exception("Error fetching quick stats")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/study-session/complete",
    summary="Record a completed study session",
)
async def complete_study_session(
    body: StudySessionRequest,
    current_user: dict = Depends(get_current_user_from_header),
):
    """
    Record a completed study session. Updates:
    - Subject progress & topic mastery
    - Activity heatmap for today
    - User streaks, points, focus score
    - Pushes real-time updates via WebSocket

    Request body:
    - subject: e.g. "Physics"
    - topic: topic_id string (use /api/mcq/topics to list valid IDs)
    - time_spent: minutes
    - mastery_achieved: 0-100
    """
    user_id = current_user["user_id"]
    try:
        result = await dashboard_service.update_study_progress(
            user_id=user_id,
            subject=body.subject,
            topic=body.topic,
            time_spent=body.time_spent,
            mastery_achieved=body.mastery_achieved,
        )

        # Push real-time updates via WebSocket (fire-and-forget)
        import asyncio
        asyncio.create_task(
            send_dashboard_event(user_id, "stats", result["stats"])
        )
        if result.get("heatmap_cell"):
            asyncio.create_task(
                send_dashboard_event(user_id, "heatmap", result["heatmap_cell"])
            )
        for notif in result.get("new_notifications", []):
            asyncio.create_task(
                send_dashboard_event(user_id, "notification", notif)
            )

        return {
            "success": True,
            "message": "Study session recorded",
            "data": {
                "updated_stats":    result["stats"],
                "heatmap_cell":     result.get("heatmap_cell"),
                "new_notifications": result.get("new_notifications", []),
            }
        }
    except Exception as e:
        logger.exception("Error completing study session")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/notifications/{notification_id}/read",
    summary="Mark a notification as read",
)
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user_from_header),
):
    """Marks the specified notification as read and returns updated unread count."""
    try:
        unread = await dashboard_service.mark_notification_read(
            current_user["user_id"], notification_id
        )
        if unread == -1:
            raise HTTPException(status_code=404, detail="Notification not found")
        return {
            "success": True,
            "data": {"notification_id": notification_id, "unread_count": unread}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error marking notification read")
        raise HTTPException(status_code=500, detail=str(e))
