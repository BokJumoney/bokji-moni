"""
Policy Search Tool.

복지 정책 관련 질문을 처리한다.
welfare_policies(정책 기본 정보)와 welfare_policy_pdf_vector(정책 상세 문서)
두 벡터 컬렉션을 동시에 검색한 뒤 결과를 병합해서 돌려준다.
"""

import asyncio

from langchain_core.tools import tool

from app.rag.policy_retriever import search_policy_info
from app.rag.pdf_retriever import policy_pdf_search


@tool
async def policy_search_tool(query: str) -> str:
    """
    복지 정책의 지원 대상, 신청 방법, 정책 설명, 구비서류, 서식,
    세부 조건 등 정책 자체에 대한 질문에 답할 때 사용한다.
    벡터DB(welfare_policies, welfare_policy_pdf_vector)를 검색한다.
    """
    policy_docs, pdf_docs = await asyncio.gather(
        search_policy_info(query),
        policy_pdf_search(query),
    )

    return _merge_documents(policy_docs, pdf_docs)


def _merge_documents(policy_docs, pdf_docs) -> str:
    sections = []

    if policy_docs:
        basic = "\n\n".join(f"- {d.page_content}" for d in policy_docs)
        sections.append(f"[정책 기본 정보]\n{basic}")

    if pdf_docs:
        detail = "\n\n".join(f"- {d.page_content}" for d in pdf_docs)
        sections.append(f"[정책 상세 문서]\n{detail}")

    if not sections:
        return "관련 정책 정보를 찾지 못했습니다."

    return "\n\n".join(sections)
