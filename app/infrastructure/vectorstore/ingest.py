"""
복지 정책 CSV 적재 모듈.

- langchain_postgres.PGVector에 임베딩+문서+메타데이터 적재
- WelfarePolicy SQLModel 테이블에 정형 메타데이터 동기화
- BM25Retriever용 원본 청크 로드

repo root에서 실행:
    python -m app.infrastructure.vectorstore.ingest
"""
import pandas as pd
from langchain_core.documents import Document
from sqlmodel import Session

from app.domain.welfare.entity.models import WelfarePolicy
from app.domain.welfare.service import parser
from app.infrastructure.config import settings
from app.infrastructure.db.connection import get_session
from app.infrastructure.vectorstore.setup_vectorstore import (
    get_vectorstore,
    _init_bm25_retriever,
    reset_retrievers,
)

#한글 csv에서 청크로
def read_csv_and_split_text( csv_path: str ) -> list[Document]:
    """
    CSV를 읽고 행별 Document를 생성한 뒤 청킹하여 반환.
    인코딩: utf-8-sig (BOM 포함 UTF-8).
    """
    print(f"CSV 읽기: {csv_path} ------")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    documents: list[Document] = []

    #csv를 청킹해서 df로 바꿈
    chunked_df = parser.chunk_dataframe(df)

    for _, row in chunked_df.iterrows():
        documents.append(
            Document(
                page_content=row["content"],
                metadata={
                    "service_id": row["service_id"],
                    "service_name": row["service_name"],
                    "chunk_type": row["chunk_type"],
                },
            )
        )

    print(f"생성된 청크 수: {len(documents)}\n")
    return documents


def load_chunks_for_bm25() -> list[Document]:
    """BM25Retriever용 원본 청크 로드."""
    return read_csv_and_split_text(settings.WELFARE_CSV_PATH)


def _sync_to_sqlmodel(chunks: list[Document]) -> None:
    """WelfarePolicy SQLModel 테이블에 정형 메타데이터 동기화."""
    session: Session = next(get_session())
    try:
        # 기존 데이터 전체 삭제 (재적재 편의)
        from sqlalchemy import delete
        session.exec(delete(WelfarePolicy))
        session.commit()

        for chunk in chunks:
            m = chunk.metadata
            session.add(WelfarePolicy(
                service_id=m["service_id"],
                service_name=m["service_name"],
                chunk_type=m["chunk_type"],
                page_content=chunk.page_content,
            ))
        session.commit()
        print(f"SQLModel 동기화 완료: {len(chunks)}행")
    finally:
        session.close()


def ingest_to_pgvector(csv_path: str | None = None) -> int:
    """
    PGVector에 CSV를 적재 + BM25Retriever 초기화 + SQLModel 동기화.
    적재된 청크 수를 반환.
    """
    path = csv_path or settings.WELFARE_CSV_PATH
    chunks = read_csv_and_split_text(path) #Document 청크를 리턴.

    if not chunks: #chunk가 비어있으면 그냥 리턴
        print("적재할 청크가 없습니다.")
        return 0

    # 캐시 초기화 (재적재 대비)
    reset_retrievers()

    # 1. PGVector 적재
    vectorstore = get_vectorstore()
    total = 0
    ids = []
    for i in range(0, len(chunks), 100):
        batch = chunks[i:i + 100]
        ids = [f"{md.metadata["service_id"]}-{md.metadata["chunk_type"]}" for md in batch]
        vectorstore.add_documents(batch, ids=ids)
        total += len(batch)
        print(f"PGVector 적재 진행: {total}/{len(chunks)}")
    print(f"PGVector 적재 완료: 총 {total}개 청크")

    # 2. BM25Retriever 초기화 (in-memory)
    _init_bm25_retriever(chunks)

    # 3. SQLModel 테이블 동기화
    _sync_to_sqlmodel(chunks)

    return total


def is_ingested() -> bool:
    """PGVector 컬렉션에 문서가 존재하는지 확인."""
    try:
        vectorstore = get_vectorstore()
        results = vectorstore.similarity_search("복지", k=1)
        return len(results) > 0
    except Exception:
        return False


def ensure_ingested() -> None:
    """앱 기동 시 호출. 컬렉션이 비어있으면 자동 적재."""
    if is_ingested():
        print("Vectorstore에 이미 데이터가 존재합니다. 적재를 건너뜁니다.")
        # BM25 retriever는 매 기동 시 재구성 필요 (in-memory)
        chunks = load_chunks_for_bm25()
        _init_bm25_retriever(chunks)
        return

    print("Vectorstore가 비어있습니다. CSV 적재를 시작합니다...")
    ingest_to_pgvector()


if __name__ == "__main__":
    from app.infrastructure.db.connection import init_db

    init_db()
    ingest_to_pgvector()