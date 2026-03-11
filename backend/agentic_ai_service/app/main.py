# app/main.py
from fastapi import FastAPI, HTTPException, Header, Depends, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError, ExpiredSignatureError
from dotenv import load_dotenv
from app.schemas.mcq import MCQRequest, MCQResponse
from app.graphs.mcq_graph import run_mcq_pipeline
from app.services.quiz_repository import save_quiz
from app.schemas.evaluation import EvaluationRequest, EvaluationResponse
from app.graphs.evaluation_graph import run_evaluation_pipeline


# Dashboard router + WebSocket
from app.routes.dashboard import router as dashboard_router
from app.ws.dashboard_ws import dashboard_ws_endpoint
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Knowscope Agentic Service",
    description=(
        "AI-powered MCQ generation, quiz evaluation, and student dashboard APIs.\n\n"
        "## MCQ Generation\n"
        "Use `GET /api/mcq/topics` to browse example topics per subject, "
        "then pass `topic_id` (any free-form string like **'Trigonometry'**) "
        "along with `class_level` (e.g. **'10'**) to `POST /api/mcq/generate`.\n\n"
        "**`POST /api/mcq/generate` requires a Bearer JWT token.**\n\n"
        "## Dashboard\n"
        "All `/api/dashboard/*` endpoints also require a Bearer JWT token."
    ),
    version="3.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers ───────────────────────────────────────────────────────────

app.include_router(dashboard_router)

# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/dashboard/{user_id}")
async def ws_dashboard(websocket: WebSocket, user_id: str, token: str = ""):
    """
    Real-time dashboard updates.
    Connect: `ws://host/ws/dashboard/{user_id}?token=<jwt>`

    Server-pushed events:
    - `connected`    — on successful handshake
    - `notification` — new AI notification
    - `stats`        — updated streaks / points / ranking
    - `heatmap`      — updated heatmap cell
    - `pong`         — response to client ping
    """
    await dashboard_ws_endpoint(websocket, user_id, token=token)



# security = HTTPBearer()
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


@app.get("/me", tags=["MCQ"])
async def read_my_profile(current_user: dict = Depends(get_current_user_from_header)):
    # current_user = {'user_id': ..., 'email': ...}
    return {"message": "Current user fetched successfully", "user": current_user}







# ── MCQ Endpoints ─────────────────────────────────────────────────────────────


@app.post(
    "/api/mcq/generate",
    response_model=MCQResponse,
    summary="Generate MCQs — requires Bearer token",
    tags=["MCQ"],
)
async def generate_mcq(
    request: MCQRequest,
    current_user: dict = Depends(get_current_user_from_header),
):
    """
    Generate multiple-choice questions for a student.

    **Authentication:** Bearer JWT required (user's quiz is stored under their account).

    **Request body example:**
    ```json
    {
      "subject": "Maths",
      "class_level": "10",
      "topic_id": "Trigonometry",
      "difficulty": "medium",
      "num_questions": 20,
      "top_k": 6
    }
    ```

    - `subject` — subject name (e.g. "Maths", "Physics", "Chemistry")
    - `class_level` — student's class as a string (e.g. "10", "12")
    - `topic_id` — any topic name (e.g. "Trigonometry", "Optics", "Polynomials")
    - `difficulty` — "easy" | "medium" | "hard"
    """
    user_id = current_user["user_id"]

    try:
        mcqs = await run_mcq_pipeline(
            subject=request.subject,
            topic=request.topic_id,         # student-chosen free-form topic
            difficulty=request.difficulty,
            num_questions=request.num_questions,
            top_k=request.top_k,
            class_level=request.class_level,
        )

        quiz_id = await save_quiz(
            user_id=user_id,
            subject=request.subject,
            class_level=request.class_level,
            topic=request.topic_id,
            difficulty=request.difficulty,
            questions=mcqs,
        )

        return {
            "quiz_id":     quiz_id,
            "user_id":     user_id,
            "subject":     request.subject,
            "class_level": request.class_level,
            "topic":       request.topic_id,
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


@app.post(
    "/api/mcq/evaluate",
    response_model=EvaluationResponse,
    summary="Evaluate a completed quiz — requires Bearer token",
    tags=["MCQ"],
)
async def evaluate_quiz(
    request: EvaluationRequest,
    current_user: dict = Depends(get_current_user_from_header),
):
    """Evaluate student answers and return score, strengths, weaknesses, and AI feedback."""
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
