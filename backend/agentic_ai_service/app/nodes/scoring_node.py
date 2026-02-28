# app/nodes/scoring_node.py

def evaluate_answers(quiz: dict, user_answers: list[int]):
    """
    Deterministic scoring.
    """

    questions = quiz["questions"]

    if len(user_answers) != len(questions):
        raise ValueError("Number of answers does not match number of questions")

    correct_count = 0
    detailed_results = []

    for idx, question in enumerate(questions):
        correct_index = question["correct_index"]
        user_index = user_answers[idx]

        is_correct = user_index == correct_index

        if is_correct:
            correct_count += 1

        detailed_results.append({
            "question": question["question"],
            "is_correct": is_correct,
            "correct_index": correct_index,
            "user_index": user_index
        })

    score_percentage = (correct_count / len(questions)) * 100

    return {
        "total_questions": len(questions),
        "correct_answers": correct_count,
        "score_percentage": round(score_percentage, 2),
        "details": detailed_results
    }