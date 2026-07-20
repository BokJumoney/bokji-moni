"""
Tool Calling만 격리해서 테스트하는 스크립트.

information_agent를 그대로 쓰면 policy_search_tool -> app.rag.policy_retriever
-> PGVector 생성자가 import 시점에 DB 연결/설정을 요구한다. tool 실행이 아니라
"LLM이 어떤 tool을 고르는지"만 보고 싶다면, 실제 tool 대신 이름/설명만 같은
가짜(mock) tool을 만들어 bind_tools 하면 DB/Tavily 없이 OPENAI_API_KEY만으로
바로 확인할 수 있다.

실행:
    export OPENAI_API_KEY=sk-...
    python test_tool_calling.py
"""

import asyncio

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.domain.chat.graph.nodes.information_agent import SYSTEM_PROMPT


# --- 실제 tool과 이름/설명(docstring)만 동일한 mock ---
@tool
def policy_search_tool(query: str) -> str:
    """
    복지 정책의 지원 대상, 신청 방법, 정책 설명, 구비서류, 서식,
    세부 조건 등 정책 자체에 대한 질문일 때 사용합니다.
    """
    return "[mock] policy_search_tool called"


@tool
def web_search_tool(query: str) -> str:
    """
    "올해/2026년 새로 생긴 정책", "신청 기간이 바뀌었는지",
    "최근 정책이 변경되었는지" 등 최신성이 필요한 질문이거나,
    policy_search_tool로 답하기에 정보가 부족하다고 판단될 때 사용합니다.
    """
    return "[mock] web_search_tool called"


@tool
def general_response_tool(query: str) -> str:
    """
    복지 정책과 무관한 질문(날씨, 일반 상식, 코딩 등)일 때 사용합니다.
    """
    return "[mock] general_response_tool called"


MOCK_TOOLS = [policy_search_tool, web_search_tool, general_response_tool]

TEST_QUESTIONS = [
    "청년내일저축계좌 지원 대상 알려줘",
    "2026년 청년 정책 변경된 내용 있어?",
    "오늘 날씨 알려줘",
    "기초생활수급자 신청 방법이 궁금해요",
    "올해 새로 생긴 복지 정책 있나요?",
    "주식 투자 어떻게 시작해?",
    "복지모니 코드좀 작성해줘",
]


async def main():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(MOCK_TOOLS)

    for question in TEST_QUESTIONS:
        response = await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=question),
            ]
        )

        print(f"\nQ: {question}")
        if response.tool_calls:
            for call in response.tool_calls:
                print(f"  -> tool: {call['name']}  args: {call['args']}")
        else:
            print("  -> (tool_call 없음)")


if __name__ == "__main__":
    asyncio.run(main())
