from fastapi import FastAPI, HTTPException
from app.schemas.mcq import MCQRequest, MCQResponse
from app.graphs.mcq_graph import run_mcq_pipeline
from app.services.quiz_repository import save_quiz
from app.schemas.evaluation import EvaluationRequest
from app.graphs.evaluation_graph import run_evaluation_pipeline

app = FastAPI(title="Knowscope Agentic Service")


@app.post("/api/mcq/generate", response_model=MCQResponse)
async def generate_mcq(request: MCQRequest):

    try:
        mcqs = await run_mcq_pipeline(
            subject=request.subject,
            topic=request.topic,
            difficulty=request.difficulty,
            num_questions=request.num_questions,
            top_k=request.top_k,
        )

        quiz_id = await save_quiz(
            subject=request.subject,
            topic=request.topic,
            difficulty=request.difficulty,
            questions=mcqs
        )

        return {
            "quiz_id": quiz_id,
            "subject": request.subject,
            "topic": request.topic,
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
    

@app.post("/api/mcq/evaluate")
async def evaluate_quiz(request: EvaluationRequest):

    try:
        result = await run_evaluation_pipeline(
            quiz_id=request.quiz_id,
            user_answers=request.user_answers
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception:
        raise HTTPException(status_code=500, detail="Evaluation failed")    