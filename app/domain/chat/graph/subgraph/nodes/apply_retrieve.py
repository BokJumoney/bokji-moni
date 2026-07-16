from app.domain.chat.graph.state import ChatGraphState
from app.infrastructure.vectorstore.setup_vectorstore import (
    get_application_retriever,
)


async def application_retrieve(state: ChatGraphState):

    print("------ APPLICATION RETRIEVE ------")

    question = state["question"]

    retriever = get_application_retriever()

    documents = retriever.invoke(question)

    print("신청 문서 검색 완료:", len(documents))

    return {
        "documents": documents
    }