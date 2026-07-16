from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.domain.chat.graph.state import ChatGraphState
from app.infrastructure.config import settings

llm = ChatOllama(
    model=settings.LOCAL_MODEL,
    base_url=settings.LOCLAL_LLM_URL,
)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            당신은 친근한 대화 파트너입니다.
            """,
        ),
        (
            "human",
            "{question}",
        ),
    ]
)

chain = prompt | llm


async def casual_talk(state: ChatGraphState):
    response = await chain.ainvoke({
            "question": state["question"]
        }
    )
    return {
        "generation": response.content
    }