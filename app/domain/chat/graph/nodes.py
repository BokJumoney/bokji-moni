from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from app.domain.chat.graph.state import GraphState
from app.infrastructure.config import settings

OLLAMA_MODEL = settings.LOCAL_MODEL
OLLAMA_BASE_URL = settings.LOCLAL_LLM_URL

llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)


async def retrieve(state: GraphState) -> dict:
    """
    벡터스토어에서 사용자 질문과 관련된 문서를 검색한다.
    현재는 벡터스토어가 연결되지 않았으므로 빈 목록을 반환한다.
    """
    return {"documents": []}


generate_prompt = ChatPromptTemplate.from_messages([
    ("system", """
        당신은 복지 정책 도우미입니다.
        아래 문서를 바탕으로 사용자의 질문에 정확하고 도움이 되는 답변을 제공하세요.
        문서에 관련 정보가 없는 경우, 일반적인 지식으로 답변하세요.
    """),
    ("human", "질문: {question}\n\n문서: {documents}"),
])

rag_chain = generate_prompt | llm


async def generate(state: GraphState) -> dict:
    """
    검색된 문서와 사용자 질문을 바탕으로 최종 답변을 생성한다.
    """
    question = state["question"]
    documents = state.get("documents", [])
    documents_text = "\n".join(documents) if documents else "관련 문서 없음"

    response = await rag_chain.ainvoke(
        {"question": question, "documents": documents_text}
    )
    return {"generation": response.content}


casual_prompt = ChatPromptTemplate.from_messages([
    ("system", """
        당신은 친근하고 따뜻한 대화 파트너입니다.
        사용자와 자연스러운 일상 대화를 나누세요.
        대화 기록을 참고하여 맥락에 맞는 답변을 제공하세요.
    """),
    ("human", "{question}"),
])

casual_chain = casual_prompt | llm


async def casual_talk(state: GraphState) -> dict:
    """
    복지 정책과 관련 없는 일상적인 대화에 대한 답변을 생성한다.
    """
    question = state["question"]
    response = await casual_chain.ainvoke({"question": question})
    return {"generation": response.content}