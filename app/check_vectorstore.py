"""
PGVector에 등록된 컬렉션과 각 컬렉션의 row 수를 직접 확인하는 진단 스크립트.

policy_search_tool에서 특정 컬렉션만 0건이 나올 때, 원인이
  1) 컬렉션 자체가 비어있음 (ingest를 안 돌렸거나 실패함)
  2) ingest할 때 쓴 collection_name이 코드에서 참조하는 이름과 다름
둘 중 무엇인지 구분하기 위한 것.

langchain-postgres의 PGVector는 내부적으로
  langchain_pg_collection (컬렉션 목록)
  langchain_pg_embedding  (실제 벡터/문서, collection_id로 연결)
두 테이블을 사용한다.

실행:
    python -m app.check_vectorstore
"""

import psycopg
from app.infrastructure.config import settings


def _plain_dsn(database_url: str) -> str:
    # "postgresql+psycopg://..." -> "postgresql://..."
    return database_url.replace("postgresql+psycopg", "postgresql", 1)


def main() -> None:
    dsn = _plain_dsn(settings.database_url)

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name, uuid FROM langchain_pg_collection ORDER BY name;")
            collections = cur.fetchall()

            if not collections:
                print("langchain_pg_collection 테이블에 컬렉션이 하나도 없습니다.")
                print("-> ingest 스크립트가 아직 한 번도 실행된 적이 없을 가능성이 높습니다.")
                return

            print("=== 등록된 컬렉션 ===")
            for name, uuid in collections:
                cur.execute(
                    "SELECT count(*) FROM langchain_pg_embedding WHERE collection_id = %s;",
                    (uuid,),
                )
                count = cur.fetchone()[0]
                print(f"  {name:35s} {count:>6}건")

            names = {name for name, _ in collections}
            for expected in ("welfare_policies", "welfare_policy_pdf_vector"):
                if expected not in names:
                    print(f"\n[경고] 코드에서 참조하는 '{expected}' 컬렉션이 DB에 없습니다.")
                    print("       ingest 시 collection_name 철자를 다시 확인하세요.")


if __name__ == "__main__":
    main()
