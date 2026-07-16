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
from sqlmodel import Session, select

from app.common.timezone import now_kst
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
    """WelfarePolicy 테이블에 정책별 한 행으로 정형 데이터를 동기화한다.

    벡터 저장소에는 검색 품질을 위해 여러 청크를 보관하지만 구독 관계는
    정책 하나를 참조해야 한다. 따라서 같은 service_id의 청크를 합쳐 한 행만
    만들며, 구독이 연결된 운영 DB에서는 전체 삭제 방식 대신 별도 마이그레이션
    전략이 필요하다.
    """
    session: Session = next(get_session())
    try:
        policies: dict[str, dict] = {}
        for chunk in chunks:
            m = chunk.metadata
            service_id = m["service_id"]
            if service_id not in policies:
                policies[service_id] = {"metadata": m, "contents": []}
            policies[service_id]["contents"].append(chunk.page_content)

        for policy in policies.values():
            m = policy["metadata"]
            existing = session.exec(
                select(WelfarePolicy).where(
                    WelfarePolicy.service_id == m["service_id"]
                )
            ).first()
            values = {
                "service_name": m["service_name"],
                "department": m["department"],
                "year": m["year"],
                "cycle": m["cycle"],
                "type": m["type"],
                "life_cycle": m["life_cycle"],
                "topic": m["topic"],
                "household_type": m["household_type"],
                "page_content": "\n\n".join(policy["contents"]),
            }
            if existing is None:
                session.add(WelfarePolicy(service_id=m["service_id"], **values))
            else:
                # 관리자가 입력한 마감일과 폐지 상태는 CSV 재적재로 덮지 않는다.
                for field, value in values.items():
                    setattr(existing, field, value)
                existing.updated_at = now_kst()
                session.add(existing)
        session.commit()
        print(f"SQLModel 동기화 완료: {len(policies)}개 정책")
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
