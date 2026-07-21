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
from pandas import DataFrame
from sqlmodel import Session, text

from app.domain.welfare.entity.models import WelfarePolicy
from app.domain.welfare.service import chunker
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
    df = df.fillna("")
    documents: list[Document] = []

    #청킹 전에 RDB 적재
    _init_sqlmodel_table(df)
    #csv를 청킹해서 df로 바꿈
    chunked_df = chunker.chunk_dataframe(df)

    for _, row in chunked_df.iterrows():
        documents.append(
            Document(
                page_content=row["content"],
                metadata={
                    "service_id": row["service_id"],
                    "service_name": row["service_name"],
                    "service_depart": row["service_depart"],
                    "service_target_household": row["service_target_household"],
                    "service_target_age": row["service_target_age"],
                    "chunk_type": row["chunk_type"]
                },
            )
        )

    print(f"생성된 청크 수: {len(documents)}\n")
    return documents


def load_chunks_for_bm25() -> list[Document]:
    """
    BM25Retriever용 전체 청크 로드.
    VectorDB collection_id - welfare_policy_vector 에서 조회한다.
    """
    session: Session = next(get_session())
    sql = '''
            SELECT e.document, e.cmetadata
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = :collection_name
    '''
    try:
        rows = session.exec(text(sql), params={"collection_name": settings.VECTOR_COLLECTION_NAME}).all()
        return [
            Document(
                page_content=row.document,
                metadata=row.cmetadata,
            )
            for row in rows
        ]
    finally:
        session.close()


def _init_sqlmodel_table(df: DataFrame) -> None:
    """WelfarePolicy SQLModel 테이블에 정형 메타데이터 동기화."""
    session: Session = next(get_session())
    try:
        # 기존 데이터 전체 삭제 (재적재 편의)
        from sqlalchemy import delete
        session.exec(delete(WelfarePolicy))
        session.commit()

        for _, row in df.iterrows():
            session.add(WelfarePolicy(
                service_id=row["서비스ID"],
                service_name=row["서비스명"],
                service_depart=row["소관부처명"],
                service_summary=row["서비스요약"],
                service_benefit=row["급여서비스내용"],
                service_target_detail=row["대상자상세내용"],
                homepage_list=row["홈페이지목록"],
                contact=row["문의처"],
            ))
        session.commit()
        print(f"SQLModel 동기화 완료: {len(df)}행")
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
    vectorstore = get_vectorstore(settings.VECTOR_COLLECTION_NAME)
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

    return total


def is_ingested() -> bool:
    session: Session = next(get_session())
    try:
        # 최초 기동 시, PGVector 테이블 자체가 없는 것도 처리한다.
        table = session.exec(text("SELECT to_regclass('langchain_pg_embedding')")).first()
        if table is None or table[0] is None:
            return False

        sql = '''
                SELECT 1
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                WHERE c.name = :collection_name
                LIMIT 1
        '''
        row = session.exec(text(sql), params={"collection_name": settings.VECTOR_COLLECTION_NAME}).first()
        if row is None:
            return False
        else:
            return True
    finally:
        session.close()


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