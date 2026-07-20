"""
welfare_policies 벡터 컬렉션 검색기.

정책 기본 정보(지원 대상 / 신청 방법 / 정책 설명 등)를 검색한다.
"""

from app.infrastructure.config import settings
from app.infrastructure.vectorstore.setup_vectorstore import get_vectorstore

policy_vectorstore = get_vectorstore(settings.VECTOR_COLLECTION_NAME)


async def search_policy_info(query: str, k: int = 5):
    """welfare_policies 컬렉션에서 정책 기본 정보를 유사도 검색한다."""
    docs = policy_vectorstore.similarity_search(query, k=k)
    return docs
