from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.domain.chat.graph.state import ChatGraphState
from app.infrastructure.config import settings

OLLAMA_MODEL = settings.LOCAL_MODEL
OLLAMA_BASE_URL = settings.LOCLAL_LLM_URL

llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_BASE_URL,
)

generate_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            당신은 복지 정책 도우미입니다.

            문서를 참고하여 답변하세요.
            문서가 없으면 일반적인 지식으로 답변하세요.
            """,
        ),
        (
            "human",
            "질문:{question}\n\n문서:{documents}",
        ),
    ]
)

rag_chain = generate_prompt | llm


async def generate(state: ChatGraphState):
    print("------ GENERATE START ------")
    question = state["question"]

    documents = state.get("documents", [])

    documents_text = "\n\n".join(
        d.page_content for d in documents
    ) if documents else "관련 문서 없음"
    print("LLM 호출 전")
    response = await rag_chain.ainvoke(
        {
            "question": question,
            "documents": documents_text,
        }
    )
    print("LLM 응답 완료")

    return {
        "generation": response.content
    }