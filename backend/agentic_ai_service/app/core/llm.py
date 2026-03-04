from langchain_groq import ChatGroq
from app.core.config import settings


def get_llm(temperature: float = 0.3):
    return ChatGroq(
        model=settings.LLM_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=temperature,
        model_kwargs={
            "response_format": {"type": "json_object"}
        }
    )