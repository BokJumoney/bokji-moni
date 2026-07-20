from langchain_openai import ChatOpenAI
from app.infrastructure.config import settings


def get_llm_gpt(model="gpt-4o-mini", temperature=0, api_key=settings.OPENAI_API_KEY, reasoning_effort= None, use_responses_api = False):

    kwargs = {}
    if reasoning_effort is not None:
        kwargs['reasoning_effort'] = reasoning_effort
    if use_responses_api:
        kwargs['use_responses_api'] = True

    return ChatOpenAI(
        model = model,
        temperature = temperature,
        api_key = api_key,
        **kwargs,
    )