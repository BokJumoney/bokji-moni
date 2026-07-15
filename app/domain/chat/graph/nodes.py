from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.domain.chat.graph.state import ChatGraphState
from app.infrastructure.config import settings
from app.infrastructure.vectorstore.setup_vectorstore import get_ensemble_retriever

OLLAMA_MODEL = settings.LOCAL_MODEL
OLLAMA_BASE_URL = settings.LOCLAL_LLM_URL

llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)


async def retrieve(state: ChatGraphState) -> dict:
    """
    vectorstore(BM25 + PGVector 하이브리드)에서 질문에 대한 문서를 검색한다.

    :param state: 현재 graph state
    :return: 검색된 문서와 사용자 질문을 포함하는 새로운 graph state
    """
    print("------ RETRIEVE ------")
    question = state["question"]

    ensemble_retriever = get_ensemble_retriever()
    documents = ensemble_retriever.invoke(question)

    for doc in documents:
        print(f" 검색 결과: {doc.metadata['service_name']}")

    return {"documents": documents, "question": question}


generate_prompt = ChatPromptTemplate.from_messages([
    ("system", """
        당신은 복지 정책 도우미입니다.
        아래 문서를 바탕으로 사용자의 질문에 정확하고 도움이 되는 답변을 제공하세요.
        문서에 관련 정보가 없는 경우, 일반적인 지식으로 답변하세요.
    """),
    ("human", "질문: {question}\n\n문서: {documents}"),
])

rag_chain = generate_prompt | llm


async def generate(state: ChatGraphState) -> dict:
    """
    검색된 문서와 사용자 질문을 바탕으로 최종 답변을 생성한다.
    """
    question = state["question"]
    documents = state.get("documents", [])
    if documents:
        documents_text = "\n\n".join(
            d.page_content if hasattr(d, "page_content") else str(d)
            for d in documents
        )
    else:
        documents_text = "관련 문서 없음"

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


async def casual_talk(state: ChatGraphState) -> dict:
    """
    복지 정책과 관련 없는 일상적인 대화에 대한 답변을 생성한다.
    """
    question = state["question"]
    response = await casual_chain.ainvoke({"question": question})
    return {"generation": response.content}