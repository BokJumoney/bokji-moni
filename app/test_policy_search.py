"""
실제 DB(PGVector)에서 정책 정보를 진짜로 꺼내올 수 있는지 확인하는 테스트.

test_tool_calling.py가 mock tool로 "Agent가 어떤 tool을 고르는지"만
확인했다면, 이 파일은 실제 policy_search_tool을 호출해서
welfare_policies / welfare_policy_pdf_vector 컬렉션에서 진짜 검색
결과가 돌아오는지 확인한다. (DB/OPENAI_API_KEY 필요, mock 없음)

원시 리트리버(search_policy_info, policy_pdf_search) 각각과,
둘을 합친 policy_search_tool을 모두 찍어봐서 어느 단계에서
문제가 있는지 바로 알 수 있게 했다.

사전 조건:
- .env에 DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD, OPENAI_API_KEY 설정
- welfare_policies, welfare_policy_pdf_vector 컬렉션에 데이터가
  이미 적재되어 있어야 함 (비어있으면 검색 결과도 0건으로 나옴)

실행:
    python -m app.test_policy_search
"""

import asyncio

from app.rag.policy_retriever import search_policy_info
from app.rag.pdf_retriever import policy_pdf_search
from app.domain.chat.graph.tools.policy_search import policy_search_tool

TEST_QUERIES = [
     "청년내일저축계좌 지원 대상 알려줘",
    "2026년 청년 정책 변경된 내용 있어?",
    "오늘 날씨 알려줘",
    "기초생활수급자 신청 방법이 궁금해요",
    "올해 새로 생긴 복지 정책 있나요?",
    "주식 투자 어떻게 시작해?",
    "복지모니 코드좀 작성해줘",

]


async def _print_docs(label: str, docs) -> None:
    print(f"\n[{label}] {len(docs)}건")
    for i, doc in enumerate(docs, 1):
        content = doc.page_content.replace("\n", " ")
        print(f"  {i}. {content[:200]}")
        if doc.metadata:
            print(f"     metadata: {doc.metadata}")


async def test_raw_retrievers(query: str) -> None:
    print(f"\n=== [원시 리트리버] {query} ===")

    policy_docs = await search_policy_info(query)
    await _print_docs("welfare_policies", policy_docs)

    pdf_docs = await policy_pdf_search(query)
    await _print_docs("welfare_policy_pdf_vector", pdf_docs)


async def test_merged_tool(query: str) -> None:
    print(f"\n=== [policy_search_tool 병합 결과] {query} ===")
    result = await policy_search_tool.ainvoke({"query": query})
    print(result)


async def main() -> None:
    for query in TEST_QUERIES:
        await test_raw_retrievers(query)
        await test_merged_tool(query)
        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
