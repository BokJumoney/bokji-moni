"""
welfare_policy_pdf_vector 벡터 컬렉션 검색기.

정책 상세 문서(구비서류 / 서식 / 세부 조건 등)를 검색한다.

참고: 기존 코드는 policy_pdf_search 내부에 search_policy_vector 라는
함수를 정의만 해두고 실제로는 호출/반환하지 않아 항상 None을 반환하는
버그가 있었다. 아래 버전은 해당 버그를 수정한 것이다.
"""

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from app.infrastructure.config import settings
from langchain_huggingface import HuggingFaceEmbeddings
from app.infrastructure.config import settings

embedding_snow = HuggingFaceEmbeddings(model_name=settings.VECTOR_EMBEDDING_MODEL_SNOW)


pdf_vectorstore = PGVector(
    embeddings=embedding_snow,
    collection_name="welfare_policy_pdf_vector",
    connection=settings.database_url,
)


async def policy_pdf_search(query: str, k: int = 5):
    """welfare_policy_pdf_vector 컬렉션에서 정책 상세 문서를 유사도 검색한다."""
    docs = pdf_vectorstore.similarity_search(query, k=k)
    return docs
