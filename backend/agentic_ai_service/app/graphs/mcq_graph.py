# app/graphs/mcq_graph.py

import asyncio
from app.nodes.question_node import generate_concept_questions
from app.nodes.retrieval_node import retrieve_valid_questions
from app.nodes.distractor_node import generate_mcq


async def run_mcq_pipeline(subject: str,
                           topic: str | None,
                           difficulty: str,
                           num_questions: int = 20,
                           top_k: int = 6):
    """
    Full MCQ generation pipeline enforcing exactly N questions and batched LLM calls.
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
        questions=questions,  # Each question is now a dict with topic_id, concept_tags
        subject=subject,
        topic=topic,
        top_k=top_k,
        required_count=num_questions
    )

    if len(grounded) < num_questions:
        raise ValueError(f"Not enough grounded questions generated: got {len(grounded)}, required {num_questions}")
        
    # We maintain strictly the required count
    grounded = grounded[:num_questions]

    # 3️⃣ Generate MCQs with exactly 4 options (in batches to avoid rate limits)
    mcqs = []
    batch_size = 5
    
    # Process exactly in batches
    for i in range(0, len(grounded), batch_size):
        batch = grounded[i:i + batch_size]
        batch_tasks = []
        
        for item in batch:
            # We need to map the original metadata back
            original_q_dict = next((q for q in questions if q.get("question") == item["question"]), {})
            concept_tags = original_q_dict.get("concept_tags", [])
            
            full_item = {
                **item,
                "concept_tags": concept_tags
            }
            batch_tasks.append(generate_mcq(full_item))

        print(f"Generating distractors for batch {i//batch_size + 1} / {(len(grounded) + batch_size - 1)//batch_size}...")
        
        # Add sleep between batches (excluding the first batch)
        if i > 0:
            await asyncio.sleep(2.5)

        try:
            batch_results = await asyncio.gather(*batch_tasks)
            mcqs.extend(batch_results)
        except Exception as e:
            print(f"Error in distractor generation batch {i//batch_size + 1}: {e}")
            if "429" in str(e):
                print("Rate limit hit during distractors. Backing off for 10 seconds...")
                await asyncio.sleep(10)
                # Retry strategy
                try:
                    batch_results = await asyncio.gather(*[
                        generate_mcq({
                            **item, 
                            "concept_tags": next((q for q in questions if q.get("question") == item["question"]), {}).get("concept_tags", [])
                        }) for item in batch
                    ])
                    mcqs.extend(batch_results)
                except Exception as retry_e:
                    print(f"Retry failed for distractor batch: {retry_e}")
                    raise retry_e
            else:
                raise e

    if len(mcqs) != num_questions:
        raise ValueError(f"Failed to generate exactly {num_questions} complete MCQs")

    print("===== GENERATED MCQS =====")
    for i, m in enumerate(mcqs):
       print(f"[{i+1}/{len(mcqs)}]", m.get("question")[:50], "...")
    print("===========================")
    return mcqs
