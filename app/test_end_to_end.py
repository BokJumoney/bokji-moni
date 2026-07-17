"""
전체 파이프라인(Tool 선택 -> 실행 -> 답변 생성) 종합 테스트.

test_agent_eval.py가 "어떤 tool을 고르는지"만 확인했다면, 이 스크립트는
information_agent -> tool_router -> tool_executor -> (post_tool_router) ->
generate 까지 실제로 다 실행해서 최종 답변(answer)까지 확인한다.

general_response_tool만 실행된 경우엔 tool_executor가 이미 answer를
채워두므로 generate(LLM 재작성)를 건너뛴다 (post_tool_router 참고).

주의:
- policy_search_tool은 실제 DB를, web_search_tool은 실제 Tavily API를
  호출하므로 비용/시간이 든다 (mock 아님).

실행:
    python -m app.test_end_to_end
"""

import asyncio

from app.domain.chat.graph.nodes.information_agent import information_agent
from app.domain.chat.graph.nodes.tool_executor import tool_executor
from app.domain.chat.graph.router.tool_router import tool_router
from app.domain.chat.graph.router.post_tool_router import post_tool_router
from app.domain.chat.graph.nodes.generate import generate  # 실제 generate.py

TEST_QUESTIONS = [
    #  "청년내일저축계좌 지원 대상 알려줘",
    # "2026년 청년 정책 변경된 내용 있어?",
    # "오늘 날씨 알려줘",
    # "기초생활수급자 신청 방법이 궁금해요",
    # "올해 새로 생긴 복지 정책 있나요?",
    # "주식 투자 어떻게 시작해?",
    # "복지모니 세션 로그인 코드 좀 작성해줘",
    # "청년내일저축계좌 신청할때 서류 뭐뭐 필요해?",
     "청년 내일 저축계좌 신청기간 알려줘",
]


def _new_state(question: str) -> dict:
    return {
        "question": question,
        "intent": "",
        "messages": [],
        "context": [],
        "answer": "",
    }


async def run_pipeline(question: str) -> dict:
    state = _new_state(question)

    # 1) Agent: tool 선택
    agent_result = await information_agent(state)
    state["messages"] = state["messages"] + agent_result["messages"]

    # 2) tool_router: 다음 노드 결정
    next_node = tool_router(state)

    # 3) 필요하면 tool 실행
    if next_node == "tool_executor":
        exec_result = await tool_executor(state)
        state["messages"] = state["messages"] + exec_result["messages"]
        state["context"] = state["context"] + exec_result["context"]
        if "answer" in exec_result:
            state["answer"] = exec_result["answer"]

    # 4) 최종 답변 생성
    # general_response_tool만 실행된 경우 tool_executor가 이미 answer를
    # 채워뒀으므로 generate(LLM 재작성)를 건너뛴다.
    if post_tool_router(state) == "generate":
        generate_result = await generate(state)
        state.update(generate_result)

    return state


async def main() -> None:
    for question in TEST_QUESTIONS:
        print(f"\n{'=' * 60}")
        print(f"Q: {question}")

        state = await run_pipeline(question)

        selected_tools = [
            call["name"]
            for msg in state["messages"]
            for call in (getattr(msg, "tool_calls", None) or [])
        ]
        print(f"선택된 tool: {selected_tools}")
        print(f"context 개수: {len(state['context'])}")
        print(f"\n[최종 답변]\n{state.get('answer', '(answer 없음)')}")


if __name__ == "__main__":
    asyncio.run(main())
