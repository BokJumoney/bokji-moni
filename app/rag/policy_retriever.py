"""
welfare_policy_vector 벡터 컬렉션 검색기.

정책 기본 정보(지원 대상 / 신청 방법 / 정책 설명 등)를 검색한다.
"""

from fastapi.concurrency import run_in_threadpool
from app.infrastructure.config import settings


async def search_policy_info(query: str, k: int = 5):
    """정책 기본정보 컬렉션에서 정책을 유사도 검색한다."""
    from app.infrastructure.vectorstore.setup_vectorstore import (
        get_vectorstore
    )

    vectorstore = get_vectorstore(settings.VECTOR_COLLECTION_NAME)
    return await run_in_threadpool(vectorstore.similarity_search, query, k)
