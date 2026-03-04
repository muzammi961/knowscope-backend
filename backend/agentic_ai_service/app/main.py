from fastapi import FastAPI, HTTPException
from app.schemas.mcq import MCQRequest, MCQResponse
from app.graphs.mcq_graph import run_mcq_pipeline
from app.services.quiz_repository import save_quiz
from app.schemas.evaluation import EvaluationRequest, EvaluationResponse
from app.graphs.evaluation_graph import run_evaluation_pipeline
from app.utils.class_topic_mapper import resolve_topic, list_supported_mappings
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Knowscope Agentic Service")


@app.get("/api/mcq/topics")
async def get_supported_topics():
    """
    Returns all supported (subject, class_level, topic_id) combinations
    that can be used as inputs to /api/mcq/generate.
    """
    return {"mappings": list_supported_mappings()}


@app.post("/api/mcq/generate", response_model=MCQResponse)
async def generate_mcq(request: MCQRequest):
    num_questions = request.num_questions or 20
    top_k = request.top_k or 4

    try:
        # Resolve class_level → topic_id via the curriculum mapper
        topic = resolve_topic(request.subject, request.class_level)

        mcqs = await run_mcq_pipeline(
            subject=request.subject,
            topic=topic,
            difficulty=request.difficulty,
            num_questions=request.num_questions,
            top_k=request.top_k,
        )

        quiz_id = await save_quiz(
            subject=request.subject,
            class_level=request.class_level,
            topic=topic,
            difficulty=request.difficulty,
            questions=mcqs
        )

        return {
            "quiz_id": quiz_id,
            "subject": request.subject,
            "class_level": request.class_level,
            "topic": topic,
            "questions": mcqs
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        import traceback
        print("========== MCQ ERROR ==========")
        traceback.print_exc()
        print("================================")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/api/mcq/evaluate", response_model=EvaluationResponse)
async def evaluate_quiz(request: EvaluationRequest):

    try:
        state = await run_evaluation_pipeline(
            student_id=request.student_id,
            quiz_id=request.quiz_id,
            user_answers=request.user_answers
        )
        
        return {
            "quiz_id": state["quiz_id"],
            "total_questions": state["total_questions"],
            "correct_answers": state["correct_answers"],
            "score_percentage": state["score"],
            "strong_areas": state["strong_topics"],
            "weak_areas": state["weak_topics"],
            "feedback": state.get("feedback", ""),
            # "improvement_suggestions": state["improvement_suggestions"], 
            "recommendations": state.get("recommendations", "")
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Evaluation failed")    




app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
