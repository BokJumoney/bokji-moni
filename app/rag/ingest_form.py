# Embedding 및 Vector DB 저장
# Document를 임베딩하여 PostgreSQL(pgvector)에 저장하고 검색

import json

from langchain_openai import OpenAIEmbeddings

from app.infrastructure.db.connection import get_connection

from pgvector.psycopg2 import register_vector



embedding_model = OpenAIEmbeddings(
    model="text-embedding-3-small"
)



# 같은 form + section 묶기
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
                "\n\n".join(
                    item["content"]
                ),

                item["metadata"],

                item["distance"]

            )

        )


    return merged





# 최초 실행 테이블 생성
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





# Document 저장
def save_documents(documents):

    init_table()


    conn = get_connection()

    register_vector(conn)

    cursor = conn.cursor()


    vectors = embedding_model.embed_documents(
        [
            doc.page_content
            for doc in documents
        ]
    )


    for doc, vector in zip(
        documents,
        vectors
    ):


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


    print(
        f"{len(documents)}개 저장 완료"
    )




# 사용자 질문 검색
def search_document(query):


    conn = get_connection()

    register_vector(conn)


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


        ORDER BY distance


        LIMIT 10

        """,

        (
            vector_string,
        )

    )



    results = cursor.fetchall()



    results = merge_results(
        results
    )



    cursor.close()

    conn.close()



    return results