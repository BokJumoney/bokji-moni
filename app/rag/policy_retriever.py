"""
welfare_policies 벡터 컬렉션 검색기.

정책 기본 정보(지원 대상 / 신청 방법 / 정책 설명 등)를 검색한다.
"""
import asyncio
from app.infrastructure.config import settings
from app.infrastructure.vectorstore.setup_vectorstore import get_vectorstore
from app.infrastructure.vectorstore.setup_vectorstore import get_ensemble_retriever

policy_vectorstore = get_vectorstore(settings.VECTOR_COLLECTION_NAME)

async def search_policy_info(query: str):
    """welfare_policies 컬렉션을 BM25+PGVector 하이브리드로 검색한다.
    get_ensemble_retriever() 내부 PGVector가 sync 모드라서 async
    메서드(ainvoke)를 쓰면 "_async_engine not found"로 터진다.
    sync invoke를 asyncio.to_thread로 돌려서 이벤트 루프는 안 막으면서
    setup_vectorstore.py는 그대로 둔다 (pdf_retriever.py와 동일한 패턴).
    """
    retriever = get_ensemble_retriever()
    docs = await asyncio.to_thread(retriever.invoke, query)
    return docs