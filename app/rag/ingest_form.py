# Embedding 및 Vector DB 저장
# Document를 임베딩하여 PostgreSQL(pgvector)에 저장하고 검색
from langchain_core.documents import Document
from sqlmodel import Session
from sqlalchemy import delete
from app.domain.welfare.entity.welfareform import WelfareForm
from app.infrastructure.db.connection import get_session
from app.infrastructure.vectorstore.setup_vectorstore import get_form_vectorstore


# 같은 form + section 묶기
def merge_results(documents: list[Document]):
    grouped = {}

    for doc in documents:
        metadata = doc.metadata

        key = (
            metadata["form_name"],
            metadata["section"]
        )

        if key not in grouped:
            grouped[key] = {
                "content": [],
                "metadata": metadata
            }

        grouped[key]["content"].append(doc.page_content)

    merged = []

    for item in grouped.values():
        merged.append({
            "content": "\n\n".join(item["content"]),
            "metadata": item["metadata"]
        })

    return merged



def _sync_to_sqlmodel(documents: list[Document]):

    session: Session = next(get_session())

    try:
        # session.exec(delete(WelfareForm))
        session.commit()

        for doc in documents:

            m = doc.metadata

            session.add(
                WelfareForm(
                    policy_code=m.get("policy_code", "yet"),
                    form_name=m.get("form_name", ""),
                    section=m.get("section", ""),
                    file_path=m.get("file_path", ""),
                    page_content=doc.page_content,
                )
            )

        session.commit()
        print(f"SQLModel 저장 완료 : {len(documents)}개")

    finally:
        session.close()




# Document 저장


def save_documents(documents):

    # 1. Vector DB 저장
    vectorstore = get_form_vectorstore()
    vectorstore.add_documents(documents)

    print(f"Vector DB 저장 완료 : {len(documents)}개")

    # 2. SQLModel 저장
    _sync_to_sqlmodel(documents)




# 사용자 질문 검색
def search_document(query):

    vectorstore = get_form_vectorstore()

    docs = vectorstore.similarity_search(
        query,
        k=10
    )

    results = merge_results(docs)

    results = rerank_by_section(
        results,
        query
    )

    return results[:1]


SECTION_ALIAS = {
    "직업 및 근무 정보": [
        "직장", "회사", "근무", "직업", "일", "고용"
    ],
    "가입자 정보": [
        "가입자", "가입한 사람", "가입 대상자", "연락처"
    ],
    "적립 및 기타정보": [
        "저축", "적립", "금액", "사용 계획"
    ]
}


def rerank_by_section(results, query):
    target_section = None

    for section, keywords in SECTION_ALIAS.items():
        if any(keyword in query for keyword in keywords):
            target_section = section
            break

    if not target_section:
        return results

    matched = []
    others = []

    for item in results:
        if item["metadata"].get("section") == target_section:
            matched.append(item)
        else:
            others.append(item)

    return matched + others