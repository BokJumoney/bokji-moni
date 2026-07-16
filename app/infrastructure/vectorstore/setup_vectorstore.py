"""
Vectorstore 설정 모듈.

- 임베딩: OpenAI text-embedding-3-small
- 벡터 DB: langchain_postgres.PGVector (pgvector)
- 검색: BM25 + PGVector 하이브리드 (EnsembleRetriever)
"""
from functools import lru_cache

from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from app.infrastructure.config import settings

embedding_snow = HuggingFaceEmbeddings(model_name=settings.VECTOR_EMBEDDING_MODEL_SNOW)


# ── 임베딩 ──────────────────────────────────────────────
# embedding = OpenAIEmbeddings(
#     model=settings.VECTOR_EMBEDDING_MODEL,
#     # api_key=settings.OPENAI_API_KEY, # 시스템 변수로 설정되어있음
# )


# ── PGVector ────────────────────────────────────────────
@lru_cache(maxsize=1) # @lru_cache: 같은 인수를 전달했던 호출 결과가 이미 캐시되어 있으면 함수를 실행하지 않고 캐시 결과를 반환
def get_vectorstore() -> PGVector:
    """langchain_postgres.PGVector 인스턴스를 반환 (싱글톤)."""
    return PGVector(
        connection=settings.database_url,
        embeddings=embedding_snow,
        collection_name=settings.VECTOR_COLLECTION_NAME,
    )


# ── BM25 (키워드 검색) ─────────────────────────────────
_bm25_retriever: BM25Retriever | None = None


def get_bm25_retriever() -> BM25Retriever:
    """
    BM25Retriever 인스턴스를 반환.
    앱 기동 시 ingest 과정에서 init_bm25_retriever() 가 호출되어 캐싱됨.
    """
    if _bm25_retriever is None:
        from app.infrastructure.vectorstore.ingest import load_chunks_for_bm25
        chunks = load_chunks_for_bm25()
        _init_bm25_retriever(chunks)
    return _bm25_retriever


def _init_bm25_retriever(chunks) -> None:
    """ingest 과정에서 청크 리스트를 받아 BM25Retriever를 초기화한다."""
    global _bm25_retriever
    _bm25_retriever = BM25Retriever.from_documents(chunks)
    _bm25_retriever.k = 3


# ── 하이브리드 검색기 (BM25 + PGVector) ────────────────
_ensemble_retriever: EnsembleRetriever | None = None


def get_ensemble_retriever() -> EnsembleRetriever:
    """
    BM25 + PGVector 앙상블 검색기를 반환 (5:5 가중치).
    retrieve 노드에서 사용.
    """
    global _ensemble_retriever
    if _ensemble_retriever is None:
        pgvector_retriever = get_vectorstore().as_retriever(
            search_kwargs={"k": 3}
        )
        bm25 = get_bm25_retriever()
        _ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25, pgvector_retriever],
            weights=[0.5, 0.5],
        )
    return _ensemble_retriever


def reset_retrievers() -> None:
    """재적재 시 캐시 초기화용."""
    global _bm25_retriever, _ensemble_retriever
    _bm25_retriever = None
    _ensemble_retriever = None
    get_vectorstore.cache_clear()


def rebuild_bm25() -> None:
    """
    DB 전체 청크로 BM25를 다시 만들고 앙상블 캐시를 비운다.
    BM25는 증분 추가가 불가하므로, API 업데이트로 정책이
    추가/폐지된 뒤 마지막에 한 번 호출한다.
    """
    from app.infrastructure.vectorstore.ingest import load_chunks_for_bm25

    global _ensemble_retriever
    _init_bm25_retriever(load_chunks_for_bm25())
    _ensemble_retriever = None  # 다음 조회 때 새 BM25로 재조립