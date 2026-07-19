from langchain_openai import ChatOpenAI
from app.infrastructure.config import settings


def get_llm_gpt(model="gpt-4o-mini", temperature=0, api_key=settings.OPENAI_API_KEY):


    return ChatOpenAI(
        model = model,
        temperature = temperature,
        api_key = api_key,
    )