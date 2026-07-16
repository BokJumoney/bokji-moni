from langchain_openai import ChatOpenAI
from app.infrastructure.config import settings


def get_llm_gpt():

    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=settings.OPENAI_API_KEY
    )