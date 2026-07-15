import json
from langchain_openai import OpenAIEmbeddings
from app.infrastructure.db.connection import get_connection
from pgvector.psycopg2 import register_vector

#사용자 질문 검색
#rerank_by_section()
# 질문에 포함된 키워드를 보고 section 점수를 추가 조정
embedding_model = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

def merge_results(results):

    grouped = {}

    for content, metadata, distance in results:

        key = (
            metadata["form_name"],
            metadata["section"]
        )


        if key not in grouped:
            grouped[key] = {
                "content": [],
                "metadata": metadata,
                "distance": distance
            }


        grouped[key]["content"].append(
            content
        )


    merged = []

    for item in grouped.values():

        merged.append(
            (
                "\n\n".join(item["content"]),
                item["metadata"],
                item["distance"]
            )
        )

    return merged

# 최초 실행 시 pgvector Extension생성 , 테이블 생성 수행
def init_table():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE EXTENSION IF NOT EXISTS vector;
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS welfare_forms
        (
            id SERIAL PRIMARY KEY,
            content TEXT,
            embedding vector(1536),
            metadata JSONB
        );
        """
    )

    conn.commit()

    cursor.close()
    conn.close()


# Document를 Embedding -> PostgreSQL 저장
def save_documents(documents):

    init_table()

    conn = get_connection()

    # pgvector 등록
    register_vector(conn)

    cursor = conn.cursor()


    for doc in documents:

        vector = embedding_model.embed_query(
            doc.page_content
        )


        cursor.execute(
            """
            INSERT INTO welfare_forms
            (
                content,
                embedding,
                metadata
            )
            VALUES
            (
                %s,
                %s,
                %s
            )
            """,
            (
                doc.page_content,
                vector,
                json.dumps(
                    doc.metadata,
                    ensure_ascii=False
                )
            )
        )


    conn.commit()

    cursor.close()
    conn.close()


# 사용자 질문과 가장 유사한 신청서 검색(코사인 유사도)
# 사용자 질문과 가장 유사한 신청서 검색
def search_document(query):

    conn = get_connection()

    cursor = conn.cursor()


    query_vector = embedding_model.embed_query(
        query
    )


    vector_string = "[" + ",".join(
        map(str, query_vector)
    ) + "]"


    cursor.execute(
"""
SELECT
    content,
    metadata,
    embedding <=> %s::vector AS distance

FROM welfare_forms

WHERE
metadata->>'has_fields' = 'true'

ORDER BY distance

LIMIT 3
""",
(
    vector_string,
)
)


    results = cursor.fetchall()
    results = merge_results(results)
    results = rerank_by_section(
        results,
        query
    )
    results = results[:1]
    cursor.close()
    conn.close()


    return results


def rerank_by_section(results, query):

    section_keywords = [
        "가입자 정보",
        "신청자 정보",
        "직업 및 근무 정보",
        "가입정보",
        "적립 및 기타정보",
        "참여 여부",
        "지원대상자 가구 세대주 인적사항"
    ]


    target_section = None


    for section in section_keywords:
        for section, keywords in SECTION_ALIAS.items():

            for keyword in keywords:

                if keyword in query:
                    target_section = section
                    break


    # section 키워드 없으면 기존 순서 유지
    if not target_section:
        return results


    def score(item):

        metadata = item[1]

        section = metadata.get("section")

        distance = item[2]


        if section == target_section:
            return distance - 0.1


        return distance


    return sorted(
        results,
        key=score
    )

SECTION_ALIAS = {
    "직업 및 근무 정보": [
        "직장",
        "회사",
        "근무",
        "직업",
        "일",
        "고용"
    ],

    "가입자 정보": [
        "가입자",
        "가입한 사람",
        "가입 대상자",
        "연락처"
    ],

    "적립 및 기타정보": [
        "저축",
        "적립",
        "금액",
        "사용 계획"
    ]
}