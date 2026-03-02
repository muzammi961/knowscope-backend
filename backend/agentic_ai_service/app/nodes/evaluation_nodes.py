# app/nodes/evaluation_nodes.py

from app.schemas.evaluation import EvaluationState
from app.core.llm import get_llm
from app.core.database import students_collection
from app.services.content_client import query_content_service
from datetime import datetime


def performance_analyzer_node(state: EvaluationState) -> EvaluationState:
    score = (state["correct_answers"] / state["total_questions"]) * 100
    state["score"] = round(score, 2)
    
    if score >= 70:
        state["performance_level"] = "strong"
    elif score >= 50:
        state["performance_level"] = "average"
    else:
        state["performance_level"] = "weak"
        
    return state


def weak_topic_identifier_node(state: EvaluationState) -> EvaluationState:
    weak_concepts = set()
    strong_concepts = set()
    
    for detail in state["details"]:
        tags = detail.get("concept_tags", [])
        
        # Fallback to topic_id if concept_tags is somehow empty
        if not tags:
            tags = [detail.get("topic_id", state.get("topic", "Unknown"))]
            
        for tag in tags:
            if not detail["is_correct"]:
                weak_concepts.add(tag)
            else:
                strong_concepts.add(tag)
                
    # A concept shouldn't be considered "strong" if they failed it on another question
    pure_strong_concepts = strong_concepts - weak_concepts
            
    state["weak_topics"] = list(weak_concepts)
    state["strong_topics"] = list(pure_strong_concepts)
    
    return state


from app.utils.json_parser import safe_json_parse

async def recommendation_node(state: EvaluationState) -> EvaluationState:
    if not state["weak_topics"]:
        state["recommendations"] = "Keep up the excellent work!"
        return state
        
    # Attempt to retrieve context for the weakest topic
    weakest_topic = state["weak_topics"][0]
    query = f"topic_id: {weakest_topic} OR {weakest_topic}"
    result = await query_content_service(question=query, top_k=3)
    
    context = result.get("answer", "") if result else ""
    
    prompt = f"""
    The student recently struggled with the topic '{weakest_topic}' in '{state['subject']}'.
    
    Reference Material Context:
    {context}
    
    Generate exactly 3 actionable, structured study recommendations to improve on this concept.
    Output plain text with bullet points, directly addressing the student.
    
    CRITICAL: YOU MUST OUTPUT EXACTLY VALID JSON.
    Format your response EXACTLY as follows:
    {{
        "recommendations": "your string containing the 3 bullet points"
    }}
    """
    
    llm = get_llm(temperature=0.4)
    response = await llm.ainvoke(prompt)
    
    try:
        data = safe_json_parse(response.content)
        state["recommendations"] = data.get("recommendations", "").strip()
    except Exception:
        state["recommendations"] = "Focus on reviewing your weak topics and practice more."
    return state


async def advancement_node(state: EvaluationState) -> EvaluationState:
    prompt = f"""
    The student recently scored {state['score']}% on a '{state['subject']}' assessment for topic '{state['topic']}'.
    They demonstrate strong mastery of the concepts.
    
    Generate exactly 2 advanced, challenging concepts or next learning steps they should pursue to further their mastery.
    Output plain text with bullet points, directly addressing the student.
    
    CRITICAL: YOU MUST OUTPUT EXACTLY VALID JSON.
    Format your response EXACTLY as follows:
    {{
        "recommendations": "your string containing the 2 bullet points"
    }}
    """
    
    llm = get_llm(temperature=0.6)
    response = await llm.ainvoke(prompt)
    
    try:
        data = safe_json_parse(response.content)
        state["recommendations"] = data.get("recommendations", "").strip()
    except Exception:
        state["recommendations"] = "You're doing great! Keep tackling advanced material in this subject."
    return state


async def mongodb_update_node(state: EvaluationState) -> EvaluationState:
    student_id = state.get("student_id")
    if not student_id:
        return state

    # Structure the history entry
    history_entry = {
        "quiz_id": state["quiz_id"],
        "subject": state["subject"],
        "topic": state["topic"],
        "score": state["score"],
        "assessed_at": datetime.utcnow()
    }

    # Increment logic for weak topics
    weakness_inc = {f"weakness_counter.{wt}": 1 for wt in state["weak_topics"]}
    
    # Update strength map logic
    strength_set = {f"topic_strength_map.{st}": "mastered" for st in state["strong_topics"]}
    strength_set.update({f"topic_strength_map.{wt}": "struggling" for wt in state["weak_topics"]})

    update_doc = {
        "$push": {"performance_history": history_entry},
        "$set": {
            "last_assessed": datetime.utcnow(),
            **strength_set
        }
    }
    
    if weakness_inc:
        update_doc["$inc"] = weakness_inc

    await students_collection.update_one(
        {"student_id": student_id},
        update_doc,
        upsert=True
    )

    return state
