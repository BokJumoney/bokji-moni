from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from app.domain.chat.graph.state import GraphState

OLLAMA_MODEL = "exaone3.5"
OLLAMA_BASE_URL = "http://localhost:11434"

llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)


async def retrieve(state: GraphState) -> dict:
    """
    벡터스토어에서 사용자 질문과 관련된 문서를 검색한다.
    현재는 벡터스토어가 연결되지 않았으므로 빈 목록을 반환한다.
    """
    return {"documents": []}


class GradeDocuments(BaseModel):
    binary_score: str = Field(description="문서 관련성 평가: yes 또는 no")


grade_prompt = ChatPromptTemplate.from_messages([
    ("system", """
        당신은 검색된 문서가 사용자 질문과 관련이 있는지 평가하는 평가자입니다.
        문서가 사용자 질문과 관련된 키워드나 의미를 포함하고 있으면 'yes', 아니면 'no'로 평가하세요.
    """),
    ("human", "문서: {document}\n\n질문: {question}"),
])

structured_llm_grader = llm.with_structured_output(GradeDocuments)


async def grade_documents(state: GraphState) -> dict:
    """
    검색된 문서들이 사용자 질문과 관련이 있는지 평가하고, 관련된 문서만 필터링한다.
    """
    question = state["question"]
    documents = state.get("documents", [])

    filtered_docs = []
    for doc in documents:
        score = await structured_llm_grader.ainvoke(
            {"document": doc, "question": question}
        )
        if score.binary_score == "yes":
            filtered_docs.append(doc)

    return {"documents": filtered_docs}


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