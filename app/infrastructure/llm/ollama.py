from langchain_ollama import ChatOllama
from app.infrastructure.config import settings


def get_llm():

    return ChatOllama(
        model=settings.LOCAL_MODEL,
        base_url=settings.LOCLAL_LLM_URL
    )