"""관리자가 업로드한 정책 PDF 벡터 컬렉션 검색기."""

from fastapi.concurrency import run_in_threadpool
from app.infrastructure.config import settings


async def policy_pdf_search(query: str, k: int = 5):
    from app.infrastructure.vectorstore.setup_vectorstore import (
        get_vectorstore,
    )

    vectorstore = get_vectorstore(settings.POLICY_PDF_COLLECTION_NAME)
    return await run_in_threadpool(vectorstore.similarity_search, query, k)
