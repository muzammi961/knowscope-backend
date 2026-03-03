# app/graphs/evaluation_graph.py

from langgraph.graph import StateGraph, END
from app.schemas.evaluation import EvaluationState
from app.services.quiz_repository import get_quiz_by_id
from app.nodes.scoring_node import evaluate_answers
from app.nodes.evaluation_nodes import (
    performance_analyzer_node,
    weak_topic_identifier_node,
    recommendation_node,
    advancement_node,
    mongodb_update_node
)
from app.nodes.feedback_node import generate_feedback
from app.core.database import evaluations_collection
from datetime import datetime


def route_performance(state: EvaluationState):
    if state["performance_level"] == "weak" or state["performance_level"] == "average":
        return "weak_path"
    return "strong_path"


# Define the Graph
workflow = StateGraph(EvaluationState)

# Add Nodes
workflow.add_node("scoring", evaluate_answers)
workflow.add_node("performance_analysis", performance_analyzer_node)
workflow.add_node("weak_topic_identifier", weak_topic_identifier_node)
workflow.add_node("recommendation", recommendation_node)
workflow.add_node("advancement", advancement_node)
workflow.add_node("feedback", generate_feedback)
workflow.add_node("mongodb_update", mongodb_update_node)

# Add Edges
workflow.set_entry_point("scoring")
workflow.add_edge("scoring", "weak_topic_identifier")
workflow.add_edge("weak_topic_identifier", "performance_analysis")

workflow.add_conditional_edges(
    "performance_analysis",
    route_performance,
    {
        "weak_path": "recommendation",
        "strong_path": "advancement"
    }
)

# Weak Path
workflow.add_edge("recommendation", "feedback")

# Strong Path
workflow.add_edge("advancement", "feedback")

# Rejoin
workflow.add_edge("feedback", "mongodb_update")
workflow.add_edge("mongodb_update", END)

# Compile
evaluation_app = workflow.compile()


async def run_evaluation_pipeline(student_id: str, quiz_id: str, user_answers: list[int]):

    quiz = await get_quiz_by_id(quiz_id)

    if not quiz:
        raise ValueError("Quiz not found")

    # Initialize State
    initial_state = {
        "student_id": student_id,
        "quiz_id": quiz_id,
        "subject": quiz.get("subject", ""),
        "topic": quiz.get("topic", "General"),
        "answers": user_answers,
        "correct_answers": 0,
        "total_questions": 0,
        "score": 0.0,
        "weak_topics": [],
        "strong_topics": [],
        "performance_level": "",
        "recommendations": "",
        "feedback": "",
        "quiz_data": quiz,
        "details": []
    }

    # Run LangGraph pipeline
    final_state = await evaluation_app.ainvoke(initial_state)

    # Store evaluation to collection (for record)
    evaluation_doc = {
        "student_id": student_id,
        "quiz_id": quiz_id,
        "subject": final_state["subject"],
        "score_percentage": final_state["score"],
        "feedback": final_state["feedback"],
        "created_at": datetime.utcnow()
    }

    await evaluations_collection.insert_one(evaluation_doc)

    return {
        "student_id": final_state["student_id"],
        "quiz_id": final_state["quiz_id"],
        "score": final_state["score"],
        "correct_answers": final_state["correct_answers"],
        "total_questions": final_state["total_questions"],
        "strong_topics": final_state.get("strong_topics", []),
        "weak_topics": final_state.get("weak_topics", []),
        "feedback": final_state["feedback"],
        "recommendations": final_state["recommendations"]
    }