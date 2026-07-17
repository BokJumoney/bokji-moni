"""
welfare_policies 벡터 컬렉션 검색기.

정책 기본 정보(지원 대상 / 신청 방법 / 정책 설명 등)를 검색한다.
"""

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from app.infrastructure.config import settings
from langchain_huggingface import HuggingFaceEmbeddings
from app.infrastructure.config import settings

embedding_snow = HuggingFaceEmbeddings(model_name=settings.VECTOR_EMBEDDING_MODEL_SNOW)

policy_vectorstore = PGVector(
    embeddings=embedding_snow,
    collection_name="welfare_policies",
    connection=settings.database_url,
)


async def search_policy_info(query: str, k: int = 5):
    """welfare_policies 컬렉션에서 정책 기본 정보를 유사도 검색한다."""
    docs = policy_vectorstore.similarity_search(query, k=k)
    return docs
