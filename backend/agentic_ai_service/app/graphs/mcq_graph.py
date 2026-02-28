# app/graphs/mcq_graph.py

import asyncio
from app.nodes.question_node import generate_concept_questions
from app.nodes.retrieval_node import retrieve_valid_questions
from app.nodes.distractor_node import generate_mcq


async def run_mcq_pipeline(subject: str,
                           topic: str | None,
                           difficulty: str,
                           num_questions: int,
                           top_k: int):
    """
    Full MCQ generation pipeline.
    """

    # 1️⃣ Generate conceptual questions (buffer strategy)
    questions = await generate_concept_questions(
        subject=subject,
        topic=topic,
        difficulty=difficulty,
        num_questions=num_questions
    )

    # 2️⃣ Retrieve grounded answers
    grounded = await retrieve_valid_questions(
        questions=questions,
        subject=subject,
        topic=topic,
        top_k=top_k,
        required_count=num_questions
    )

    if len(grounded) < num_questions:
        raise ValueError("Not enough grounded questions generated")

    # 3️⃣ Generate MCQs (parallel)
    mcq_tasks = [
        generate_mcq(item["question"], item["answer"])
        for item in grounded
    ]

    mcqs = await asyncio.gather(*mcq_tasks)

    print("===== GENERATED MCQS =====")
    for m in mcqs:
       print(m)
    print("===========================")
    return mcqs
