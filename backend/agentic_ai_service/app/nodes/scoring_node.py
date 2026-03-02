# app/nodes/scoring_node.py

from app.schemas.evaluation import EvaluationState

def evaluate_answers(state: EvaluationState) -> EvaluationState:
    """
    Deterministic scoring node compatible with LangGraph.
    Accepts user_answers as either raw ints (indexes) or objects (question string, selected_option string).
    """
    quiz = state["quiz_data"]
    user_answers = state["answers"]
    questions = quiz["questions"]

    if len(user_answers) != len(questions):
        raise ValueError("Number of answers does not match number of questions")

    correct_count = 0
    detailed_results = []

    for idx, question in enumerate(questions):
        correct_index = question["correct_index"]
        topic_id = question.get("topic_id", quiz.get("topic", ""))
        
        # Parse what the user sent
        user_input = user_answers[idx]
        user_index = -1
        
        if isinstance(user_input, int):
            user_index = user_input
        elif isinstance(user_input, dict):
            # Try to map the string option to the index
            selected_option = user_input.get("selected_option")
            options = question.get("options", [])
            for opt_idx, opt in enumerate(options):
                if opt == selected_option:
                    user_index = opt_idx
                    break
        elif hasattr(user_input, "selected_option"):
            # Handle Pydantic UserAnswer object directly if not converted to dict
            selected_option = user_input.selected_option
            options = question.get("options", [])
            for opt_idx, opt in enumerate(options):
                if opt == selected_option:
                    user_index = opt_idx
                    break

        is_correct = user_index == correct_index

        if is_correct:
            correct_count += 1

        detailed_results.append({
            "question": question["question"],
            "is_correct": is_correct,
            "correct_index": correct_index,
            "user_index": user_index,
            "topic_id": topic_id,
            "concept_tags": question.get("concept_tags", [])
        })

    state["correct_answers"] = correct_count
    state["details"] = detailed_results
    state["total_questions"] = len(questions)

    return state