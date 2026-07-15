from app.domain.chat.graph.state import ChatGraphState
from app.infrastructure.vectorstore.setup_vectorstore import (
    get_ensemble_retriever,
)


async def retrieve(state: ChatGraphState):

    print("------ RETRIEVE ------")

    question = state["question"]

    retriever = get_ensemble_retriever()
    print("retriever 생성 완료")

    documents = retriever.invoke(question)
    print("검색 완료")
    print(len(documents))
    return {
        "documents": documents,
        "question": question,
    }