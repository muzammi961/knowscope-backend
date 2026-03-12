# app/main.py
"""
Knowscope Agentic Service — main entry point.
Routers:
  - MCQ generation  :  POST /api/mcq/generate   (requires Bearer token)
  - MCQ evaluation  :  POST /api/mcq/evaluate    (requires Bearer token)
  - Dashboard       :  GET  /api/dashboard/*     (requires Bearer token)
  - Study tracking  :  POST /api/study/session   (requires Bearer token)
  - Quiz submit     :  POST /api/quiz/submit      (requires Bearer token)
  - Profile         :  GET  /me                  (requires Bearer token)
"""

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError, ExpiredSignatureError
from dotenv import load_dotenv
import os

from app.schemas.mcq import MCQRequest, MCQResponse
from app.graphs.mcq_graph import run_mcq_pipeline
from app.services.quiz_repository import save_quiz
from app.schemas.evaluation import EvaluationRequest, EvaluationResponse
from app.graphs.evaluation_graph import run_evaluation_pipeline

# Routers
from app.routes.dashboard import router as dashboard_router
from app.routes.study import router as study_router

load_dotenv()

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Knowscope Agentic Service",
    description=(
        "## AI-Powered Learning Platform Backend\n\n"
        "### MCQ Generation\n"
        "`POST /api/mcq/generate` — requires Bearer JWT. "
        "Pass any topic string freely:\n"
        "```json\n"
        '{"subject":"Maths","class_level":"10","topic":"Statistics",'
        '"difficulty":"medium","num_questions":20,"top_k":6}\n'
        "```\n\n"
        "### Dashboard\n"
        "All `/api/dashboard/*` and `/api/study/*` and `/api/quiz/*` require Bearer JWT."
    ),
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers ───────────────────────────────────────────────────────────

app.include_router(dashboard_router)
app.include_router(study_router)

# ── JWT Auth (shared for MCQ + /me endpoints) ─────────────────────────────────

SECRET_KEY = os.getenv("JWT_SECRET", "")
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


# ── Profile endpoint ──────────────────────────────────────────────────────────

@app.get("/me", tags=["Auth"], summary="Get current user from token")
async def read_my_profile(current_user: dict = Depends(get_current_user_from_header)):
    return {"message": "Current user fetched successfully", "user": current_user}


# ── MCQ Generation ─────────────────────────────────────────────────────────────

@app.post(
    "/api/mcq/generate",
    response_model=MCQResponse,
    tags=["MCQ"],
    summary="Generate MCQs — requires Bearer token",
)
async def generate_mcq(
    request: MCQRequest,
    current_user: dict = Depends(get_current_user_from_header),
):
    """
    Generate multiple-choice questions for any subject and topic.

    **Request body:**
    ```json
    {
      "subject": "Maths",
      "class_level": "10",
      "topic": "Statistics",
      "difficulty": "medium",
      "num_questions": 20,
      "top_k": 6
    }
    ```
    - `topic` is a **free-form string** — the student writes whatever topic they want.
    - No predefined topic list. No backend auto-selection.
    - The generated quiz is stored in MongoDB under the student's `user_id`.
    """
    user_id = current_user["user_id"]
    try:
        mcqs = await run_mcq_pipeline(
            subject=request.subject,
            topic=request.topic,
            difficulty=request.difficulty,
            num_questions=request.num_questions,
            top_k=request.top_k,
            class_level=request.class_level,
        )

        quiz_id = await save_quiz(
            user_id=user_id,
            subject=request.subject,
            class_level=request.class_level,
            topic=request.topic,
            difficulty=request.difficulty,
            questions=mcqs,
        )

        return {
            "quiz_id":     quiz_id,
            "user_id":     user_id,
            "subject":     request.subject,
            "class_level": request.class_level,
            "topic":       request.topic,
            "difficulty":  request.difficulty,
            "questions":   mcqs,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        print("========== MCQ ERROR ==========")
        traceback.print_exc()
        print("================================")
        raise HTTPException(status_code=500, detail=str(e))


# ── MCQ Evaluation ─────────────────────────────────────────────────────────────

@app.post(
    "/api/mcq/evaluate",
    response_model=EvaluationResponse,
    tags=["MCQ"],
    summary="Evaluate quiz answers — requires Bearer token",
)
async def evaluate_quiz(
    request: EvaluationRequest,
    current_user: dict = Depends(get_current_user_from_header),
):
    """
    Evaluate student answers and return score, strengths, weaknesses, AI feedback.
    After calling this, you should also call `POST /api/quiz/submit` to persist
    mastery scores and update the student's dashboard.
    """
    try:
        state = await run_evaluation_pipeline(
            student_id=request.student_id,
            quiz_id=request.quiz_id,
            user_answers=request.user_answers,
        )
        return {
            "quiz_id":          state["quiz_id"],
            "total_questions":  state["total_questions"],
            "correct_answers":  state["correct_answers"],
            "score_percentage": state["score"],
            "strong_areas":     state["strong_topics"],
            "weak_areas":       state["weak_topics"],
            "feedback":         state.get("feedback", ""),
            "recommendations":  state.get("recommendations", ""),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Evaluation failed")
