"""
welfare_policy_pdf_vector 벡터 컬렉션 검색기.

정책 상세 문서(구비서류 / 서식 / 세부 조건 등)를 검색한다.
"""
import asyncio
from app.infrastructure.vectorstore.setup_vectorstore import get_huggingface_vectorstore


async def policy_pdf_search(query: str, k: int = 5):
    """welfare_policy_pdf_vector 컬렉션에서 정책 상세 문서를 유사도 검색한다."""
    pdf_vectorstore = get_huggingface_vectorstore()
    docs = await asyncio.to_thread(pdf_vectorstore.similarity_search, query, k)
    return docs