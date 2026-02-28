# from openai import AsyncOpenAI
# import os
# from typing import List, Dict, Any
# from dotenv import load_dotenv

# load_dotenv()

# # Read API key from environment (set OPENAI_API_KEY in your .env file)
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# # Initialize async OpenAI client (openai v1+)
# client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# class GPTService:
#     @staticmethod
#     async def generate_answer(
#         question: str,
#         context_chunks: List[Dict[str, Any]]
#     ) -> Dict[str, Any]:
#         """
#         Generate answer using GPT based on retrieved chunks.
#         Falls back to raw context if OPENAI_API_KEY is not set.
#         """
#         if not context_chunks:
#             return {
#                 "answer": "No answer found in textbook.",
#                 "sources": []
#             }

#         # Build context string from all retrieved chunks
#         context_parts = []
#         for i, chunk in enumerate(context_chunks):
#             metadata = chunk['metadata']
#             context_parts.append(
#                 f"[Source {i+1} — {metadata.get('chapter_title', 'Chapter')} / "
#                 f"{metadata.get('topic_title', 'Topic')}]:\n{chunk['text']}"
#             )

#         context = "\n\n".join(context_parts)

#         # Prepare sources for response
#         sources = []
#         for chunk in context_chunks:
#             sources.append({
#                 "chapter": chunk['metadata'].get('chapter_title', 'Unknown'),
#                 "topic": chunk['metadata'].get('topic_title', 'Unknown'),
#                 "similarity": chunk.get('similarity', 0),
#                 "text_preview": chunk['text'][:150] + "..."
#             })

#         # Fallback if no API key configured
#         if not client:
#             fallback_answer = (
#                 "⚠️ OpenAI API key not configured. "
#                 "Here are the most relevant textbook passages:\n\n" + context
#             )
#             return {"answer": fallback_answer, "sources": sources}

#         # Build RAG prompt
#         prompt = f"""You are an educational assistant helping school students prepare for exams.
# Answer the student's question using ONLY the textbook content provided below.

# TEXTBOOK CONTEXT:
# {context}

# STUDENT QUESTION: {question}

# INSTRUCTIONS:
# 1. Use ONLY the information from the textbook context above. Do not use any external knowledge.
# 2. If the context does not contain enough information to answer the question, respond exactly with: "No answer found in textbook."
# 3. Write a clear, well-structured, exam-style answer:
#    - Use proper headings or numbered points where appropriate.
#    - Define key terms clearly.
#    - Be concise but complete — aim for a model answer a student can learn from.
# 4. Do not mention retrieval, sources, or any technical process.
# 5. Write in a tone appropriate for a student textbook.

# ANSWER:"""

#         try:
#             response = await client.chat.completions.create(
#                 model="gpt-3.5-turbo",
#                 messages=[
#                     {
#                         "role": "system",
#                         "content": (
#                             "You are a helpful educational assistant that answers "
#                             "student questions strictly based on textbook content."
#                         )
#                     },
#                     {"role": "user", "content": prompt}
#                 ],
#                 temperature=0.3,
#                 max_tokens=1000
#             )

#             answer = response.choices[0].message.content
#             return {"answer": answer, "sources": sources}

#         except Exception as e:
#             return {
#                 "answer": f"Error generating answer: {str(e)}",
#                 "sources": sources
#             }


# # Initialize GPT service
# gpt_service = GPTService()





from groq import AsyncGroq
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Read API key from environment (.env file)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# Initialize async Groq client
client = AsyncGroq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


class GPTService:
    @staticmethod
    async def generate_answer(
        question: str,
        context_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate answer using Groq LLM based on retrieved chunks.
        Falls back to raw context if GROQ_API_KEY is not set.
        """

        if not context_chunks:
            return {
                "answer": "No answer found in textbook.",
                "sources": []
            }

        # Build context string
        context_parts = []
        for i, chunk in enumerate(context_chunks):
            metadata = chunk["metadata"]
            context_parts.append(
                f"[Source {i+1} — {metadata.get('chapter_title', 'Chapter')} / "
                f"{metadata.get('topic_title', 'Topic')}]:\n{chunk['text']}"
            )

        context = "\n\n".join(context_parts)

        # Prepare sources
        sources = []
        for chunk in context_chunks:
            sources.append({
                "chapter": chunk["metadata"].get("chapter_title", "Unknown"),
                "topic": chunk["metadata"].get("topic_title", "Unknown"),
                "similarity": chunk.get("similarity", 0),
                "text_preview": chunk["text"][:150] + "..."
            })

        # Fallback if no API key
        if not client:
            fallback_answer = (
                "⚠️ Groq API key not configured. "
                "Here are the most relevant textbook passages:\n\n" + context
            )
            return {"answer": fallback_answer, "sources": sources}

        # Build RAG prompt
        prompt = f"""You are an educational assistant helping school students prepare for exams.
Answer the student's question using ONLY the textbook content provided below.

TEXTBOOK CONTEXT:
{context}

STUDENT QUESTION: {question}

INSTRUCTIONS:
1. Use ONLY the information from the textbook context above.
2. If the context does not contain enough information to answer the question, respond exactly with: "No answer found in textbook."
3. Write a clear, well-structured, exam-style answer.
4. Do not mention retrieval, sources, or any technical process.
5. Write in textbook style.

ANSWER:"""

        try:
            # 🔥 Updated Groq model (working models)
            response = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",   # latest working model
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful educational assistant."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            answer = response.choices[0].message.content

            return {
                "answer": answer,
                "sources": sources
            }

        except Exception as e:
            return {
                "answer": f"Error generating answer: {str(e)}",
                "sources": sources
            }


# Initialize service
gpt_service = GPTService()