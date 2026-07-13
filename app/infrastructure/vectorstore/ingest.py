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
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlmodel import Session

from app.domain.welfare.entity.models import WelfarePolicy
from app.infrastructure.config import settings
from app.infrastructure.db.connection import get_session
from app.infrastructure.vectorstore.setup_vectorstore import (
    get_vectorstore,
    _init_bm25_retriever,
    reset_retrievers,
)


def read_csv_and_split_text(
    csv_path: str,
    chunk_size: int = settings.CHUNK_SIZE,
    chunk_overlap: int = settings.CHUNK_OVERLAP,
) -> list[Document]:
    """
    CSV를 읽고 행별 Document를 생성한 뒤 청킹하여 반환.
    인코딩: utf-8-sig (BOM 포함 UTF-8).
    """
    print(f"CSV 읽기: {csv_path} ------")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    documents: list[Document] = []

    for _, row in df.iterrows():
        metadata = {
            "service_id": str(row["서비스ID"]),
            "service_name": str(row["서비스명"]),
            "department": str(row["소관부처명"]),
            "year": int(row["기준연도"]) if pd.notnull(row["기준연도"]) else 0,
            "cycle": str(row["지원주기"]) if pd.notnull(row["지원주기"]) else "",
            "type": str(row["제공유형"]) if pd.notnull(row["제공유형"]) else "",
            "life_cycle": str(row["생애주기"]) if pd.notnull(row["생애주기"]) else "",
            "topic": str(row["관심주제"]) if pd.notnull(row["관심주제"]) else "",
            "household_type": str(row["가구유형"]) if pd.notnull(row["가구유형"]) else "",
        }

        page_content = f"""
[서비스명: {row['서비스명']}]
소관부처: {row['소관부처명']}
서비스 요약: {row['서비스요약']}

# 대상자 상세 내용
{row['대상자상세내용']}

# 선정 기준 및 자격 요건
{row['선정기준내용']}

# 급여 및 서비스 내용 (지원 혜택)
{row['급여서비스내용']}

# 신청 절차 및 방법
{row['처리절차']}

# 안내 및 문의
- 문의처: {row['문의처']}
- 문의처 목록: {row['문의처목록']}
- 홈페이지: {row['홈페이지목록']}
- 근거 법령: {row['근거법령목록']}
        """.strip()

        documents.append(Document(page_content=page_content, metadata=metadata))

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n# ", "\n\n", "\n", " ", ""],
    )
    split_docs = text_splitter.split_documents(documents)
    print(f"생성된 청크 수: {len(split_docs)}\n")
    return split_docs


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
                department=m["department"],
                year=m["year"],
                cycle=m["cycle"],
                type=m["type"],
                life_cycle=m["life_cycle"],
                topic=m["topic"],
                household_type=m["household_type"],
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
    chunks = read_csv_and_split_text(path)

    if not chunks:
        print("적재할 청크가 없습니다.")
        return 0

    # 캐시 초기화 (재적재 대비)
    reset_retrievers()

    # 1. PGVector 적재
    vectorstore = get_vectorstore()
    total = 0
    for i in range(0, len(chunks), 100):
        batch = chunks[i:i + 100]
        vectorstore.add_documents(batch)
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