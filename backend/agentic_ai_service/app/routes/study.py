# app/routes/study.py
"""
Study session and quiz submission endpoints.
"""

from __future__ import annotations
import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from jose import jwt, JWTError, ExpiredSignatureError

from app.schemas.dashboard import (
    StudySessionRequest,
    StudySessionResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
)
from app.services import dashboard_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Study & Quiz"])

_SECRET_KEY = os.getenv("JWT_SECRET", "")
_ALGORITHM  = os.getenv("JWT_ALGORITHM", "HS256")


async def get_current_user(authorization: str = Header(...)) -> dict:
    authorization = authorization.strip()
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header. Expected: Bearer <token>")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return {"user_id": str(user_id), "email": payload.get("email"), "role": payload.get("role")}
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post(
    "/api/study/session",
    response_model=StudySessionResponse,
    summary="Log a study session",
)
async def log_study_session(
    body: StudySessionRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Record a study session for the authenticated user.

    Request body:
    ```json
    {
      "subject": "Physics",
      "duration_minutes": 45,
      "topics_covered": ["Optics", "Refraction"]
    }
    ```
    Points are earned at 1 pt/minute. Streak is updated automatically.
    """
    try:
        session_id = await dashboard_service.log_study_session(
            user_id=current_user["user_id"],
            subject=body.subject,
            duration_minutes=body.duration_minutes,
            topics_covered=body.topics_covered,
        )
        return {"session_id": session_id, "message": "Study session logged successfully"}
    except Exception as e:
        logger.exception("log_study_session error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/quiz/submit",
    response_model=QuizSubmitResponse,
    summary="Submit quiz results and update mastery scores",
)
async def submit_quiz(
    body: QuizSubmitRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Submit a completed quiz. This will:
    - Record a QuizAttempt document
    - Upsert the MasteryScore for the topic (rolling weighted average)
    - Update user streak and total points
    - Return updated mastery_level, points_earned, and streak

    Request body:
    ```json
    {
      "quiz_id": "67c1...",
      "subject": "Maths",
      "class_level": "10",
      "topic": "Trigonometry",
      "difficulty": "medium",
      "score_percentage": 85.0,
      "questions_answered": 20
    }
    ```
    """
    try:
        result = await dashboard_service.record_quiz_attempt(
            user_id=current_user["user_id"],
            quiz_id=body.quiz_id,
            subject=body.subject,
            class_level=body.class_level,
            topic=body.topic,
            difficulty=body.difficulty,
            score_percentage=body.score_percentage,
            questions_answered=body.questions_answered,
        )
        return {
            "message":       "Quiz submitted successfully",
            "mastery_level": result["mastery_level"],
            "points_earned": result["points_earned"],
            "streak":        result["streak"],
        }
    except Exception as e:
        logger.exception("submit_quiz error")
        raise HTTPException(status_code=500, detail=str(e))
