"""PDF 벡터 컬렉션을 현재 OpenAI 임베딩 모델로 안전하게 재색인한다.

저장소 루트에서 실행:
    python -m app.infrastructure.vectorstore.reindex_pdf
"""

from langchain_core.documents import Document
from langchain_postgres import PGVector
from sqlalchemy import create_engine, text

from app.infrastructure.config import settings
from app.infrastructure.vectorstore.setup_vectorstore import embedding


def _load_source_documents(engine) -> tuple[list[Document], set[int]]:
    query = text(
        """
        SELECT
            e.document,
            e.cmetadata,
            vector_dims(e.embedding) AS dimension
        FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c ON c.uuid = e.collection_id
        WHERE c.name = :collection_name
        ORDER BY e.id
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {"collection_name": settings.VECTOR_PDF_COLLECTION_NAME},
        ).all()

    documents = [
        Document(page_content=row.document, metadata=row.cmetadata or {})
        for row in rows
    ]
    dimensions = {row.dimension for row in rows}
    return documents, dimensions


def _validate_temporary_collection(engine, collection_name: str, expected: int) -> None:
    query = text(
        """
        SELECT count(*) AS row_count,
               min(vector_dims(e.embedding)) AS min_dimension,
               max(vector_dims(e.embedding)) AS max_dimension
        FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c ON c.uuid = e.collection_id
        WHERE c.name = :collection_name
        """
    )
    with engine.connect() as connection:
        row = connection.execute(
            query,
            {"collection_name": collection_name},
        ).one()

    if (
        row.row_count != expected
        or row.min_dimension != settings.VECTOR_EMBEDDING_DIMENSION
        or row.max_dimension != settings.VECTOR_EMBEDDING_DIMENSION
    ):
        raise RuntimeError(
            "임시 PDF 컬렉션 검증 실패: "
            f"건수={row.row_count}/{expected}, "
            f"차원={row.min_dimension}~{row.max_dimension}"
        )


def _replace_collection(engine, temporary_name: str) -> None:
    with engine.begin() as connection:
        original_id = connection.execute(
            text(
                """
                SELECT uuid
                FROM langchain_pg_collection
                WHERE name = :name
                FOR UPDATE
                """
            ),
            {"name": settings.VECTOR_PDF_COLLECTION_NAME},
        ).scalar_one_or_none()
        temporary_id = connection.execute(
            text(
                """
                SELECT uuid
                FROM langchain_pg_collection
                WHERE name = :name
                FOR UPDATE
                """
            ),
            {"name": temporary_name},
        ).scalar_one()

        if original_id is not None:
            connection.execute(
                text("DELETE FROM langchain_pg_collection WHERE uuid = :uuid"),
                {"uuid": original_id},
            )
        connection.execute(
            text(
                """
                UPDATE langchain_pg_collection
                SET name = :original_name
                WHERE uuid = :uuid
                """
            ),
            {
                "original_name": settings.VECTOR_PDF_COLLECTION_NAME,
                "uuid": temporary_id,
            },
        )


def reindex_pdf_collection() -> int:
    """기존 PDF 문서를 1536차원 OpenAI 임베딩으로 재색인한다."""
    engine = create_engine(settings.database_url)
    documents, source_dimensions = _load_source_documents(engine)

    if not documents:
        print("재색인할 PDF 문서가 없습니다.")
        return 0
    if source_dimensions == {settings.VECTOR_EMBEDDING_DIMENSION}:
        print("PDF 컬렉션이 이미 현재 임베딩 차원을 사용하고 있습니다.")
        return len(documents)

    temporary_name = f"{settings.VECTOR_PDF_COLLECTION_NAME}__openai_reindex"
    temporary_store = PGVector(
        connection=settings.database_url,
        embeddings=embedding,
        collection_name=temporary_name,
        pre_delete_collection=True,
    )

    for start in range(0, len(documents), 100):
        end = start + 100
        # langchain_pg_embedding.id는 컬렉션과 무관한 전역 PK이므로,
        # 원본과 임시 컬렉션이 공존하는 동안 새 ID를 발급받는다.
        temporary_store.add_documents(documents[start:end])
        print(f"PDF 재색인 진행: {min(end, len(documents))}/{len(documents)}")

    _validate_temporary_collection(engine, temporary_name, len(documents))
    _replace_collection(engine, temporary_name)
    print(f"PDF 재색인 완료: {len(documents)}건")
    return len(documents)


if __name__ == "__main__":
    reindex_pdf_collection()
