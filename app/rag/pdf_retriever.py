"""
welfare_policy_pdf_vector 벡터 컬렉션 검색기.

정책 상세 문서(구비서류 / 서식 / 세부 조건 등)를 검색한다.

참고: 기존 코드는 policy_pdf_search 내부에 search_policy_vector 라는
함수를 정의만 해두고 실제로는 호출/반환하지 않아 항상 None을 반환하는
버그가 있었다. 아래 버전은 해당 버그를 수정한 것이다.
"""

from app.infrastructure.vectorstore.setup_vectorstore import (
    get_huggingface_vectorstore,
)

pdf_vectorstore = get_huggingface_vectorstore()
from fastapi.concurrency import run_in_threadpool
from app.infrastructure.config import settings


async def policy_pdf_search(query: str, k: int = 5):
    from app.infrastructure.vectorstore.setup_vectorstore import (
        get_vectorstore,
    )

    vectorstore = get_vectorstore(settings.VECTOR_PDF_COLLECTION_NAME)
    return await run_in_threadpool(vectorstore.similarity_search, query, k)
