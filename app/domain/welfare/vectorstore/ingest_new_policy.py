"""
API 정책 증분 업데이트 모듈 (신규 추가 / 폐지 삭제).

- 신규: 청킹된 DataFrame을 Document로 변환해 PGVector 추가 + SQLModel 동기화
- 폐지: service_id 목록으로 PGVector 청크 삭제
- BM25 재빌드는 폐지/신규 반영이 모두 끝난 뒤
  서비스 흐름(rag_update/service.py)에서 rebuild_bm25()로 수행
"""
from langchain_core.documents import Document
from pandas import DataFrame
from sqlmodel import Session

from app.domain.welfare.entity.models import WelfarePolicy
from app.domain.welfare.service import chunker
from app.infrastructure.db.connection import get_session
from app.infrastructure.vectorstore.setup_vectorstore import get_vectorstore

#청킹된 df -> document로
def parse_to_document( chunked_df:DataFrame ) -> list[Document]:
    documents: list[Document] = []
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
    print(f"[new policy]생성된 청크 수: {len(documents)}\n")

    return documents


def _sync_to_sqlmodel(chunks: list[Document]) -> None:
    """WelfarePolicy SQLModel 테이블에 신규 청크 추가."""
    session: Session = next(get_session())
    try:
        for chunk in chunks:
            m = chunk.metadata
            session.add(WelfarePolicy(
                service_id=m["service_id"],
                service_name=m["service_name"],
                chunk_type=m["chunk_type"],
                page_content=chunk.page_content,
            ))
        session.commit()
        print(f"[new policy]SQLModel 동기화 완료: {len(chunks)}행")
    finally:
        session.close()


def ingest_to_pgvector(chunked_df: DataFrame) -> int:
    """
    신규 정책 청크를 PGVector에 추가 + SQLModel 동기화.
    적재된 청크 수를 반환.
    """
    chunks = parse_to_document(chunked_df) #청크를 Document로 변환하여 리턴.

    if not chunks: #chunk가 비어있으면 그냥 리턴
        print("적재할 청크가 없습니다.")
        return 0

    # 1. PGVector에 신규 청크 추가
    vectorstore = get_vectorstore()
    ids = [f"{chunk.metadata["service_id"]}-{chunk.metadata["chunk_type"]}" for chunk in chunks]
    vectorstore.add_documents(chunks, ids=ids)
    print(f"[new policy]PGVector 적재 완료: 총 {len(chunks)}개 청크")

    # 2. SQLModel 테이블 동기화 (BM25 재빌드의 원본)
    _sync_to_sqlmodel(chunks)

    return len(chunks)


def delete_from_pgvector(service_ids: list[str]) -> None:
    """폐지 정책의 청크를 PGVector에서 삭제."""
    if not service_ids:
        return

    # id 규칙 {service_id}-{chunk_type}로 정책당 5청크 id 생성.
    # 빈 필드라 적재 안 된 청크의 id가 섞여 있어도 delete는 무시하고 지나감.
    ids = [
        f"{service_id}-{chunk_type}"
        for service_id in service_ids
        for chunk_type in chunker.CHUNK_FIELD_MAP
    ]
    get_vectorstore().delete(ids=ids)
    print(f"[expired policy]PGVector 삭제 완료: 정책 {len(service_ids)}건")
