"""
병렬 tool 호출(정책+최신성 동시 필요한 질문에서 policy_search_tool과
web_search_tool을 함께 호출하는 기능) 검증용 테스트.

아래 5가지를 확인한다.
  1) 재현율   - 둘 다 필요한 질문에서 실제로 둘 다 호출되는가
  2) 정밀도   - 하나만 필요한 질문에서 괜히 둘 다 부르지 않는가 (회귀)
  3) 배타성   - general_response_tool이 다른 tool과 같이 호출되지 않는가
  4) 병렬 실행 - tool_executor가 순차가 아니라 진짜 동시에 도는가
  5) 답변 품질 - 두 tool 결과가 하나의 자연스러운 답으로 합쳐지는가 (정성 평가)

사전 조건: information_agent.py의 SYSTEM_PROMPT가 "반드시 하나만 호출"이
아니라 "필요하면 policy_search_tool과 web_search_tool을 함께 호출해도
된다"로 되어 있어야 한다. 아래처럼 되어 있는지 확인:

    질문이 정책 내용과 최신성(변경 여부, 신규 정책 등)을 동시에 묻고 있다면
    policy_search_tool과 web_search_tool을 함께(동시에) 호출해도 됩니다.

실행:
    python -m app.test_multi_tool
"""

import asyncio
import time

from app.domain.chat.graph.nodes.information_agent import information_agent
from app.domain.chat.graph.nodes.tool_executor import tool_executor
from app.domain.chat.graph.router.tool_router import tool_router
from app.domain.chat.graph.router.post_tool_router import post_tool_router
from app.domain.chat.graph.nodes.generate import generate
from app.domain.chat.graph.tools.policy_search import policy_search_tool
from app.domain.chat.graph.tools.web_search import web_search_tool


def _new_state(question: str) -> dict:
    return {
        "question": question,
        "intent": "",
        "messages": [],
        "context": [],
        "answer": "",
    }


async def _select_tools(question: str) -> list:
    state = _new_state(question)
    result = await information_agent(state)
    message = result["messages"][0]
    return [call["name"] for call in (message.tool_calls or [])]


# ---------------------------------------------------------------------
# 1) 재현율: 둘 다 필요한 질문에서 실제로 둘 다 호출되는가
# ---------------------------------------------------------------------
DUAL_NEED_QUESTIONS = [
    "청년내일저축계좌 조건이 올해 바뀌었나요?",
    "기초생활수급자 지원 내용 알려주고 최근에 바뀐 점도 같이 알려줘",
    "청년월세지원 신청 방법 알려주고 예산이 올해 늘었는지도 궁금해",
]


async def test_recall() -> None:
    print("\n" + "=" * 60)
    print("[1] 재현율: 둘 다 필요한 질문에서 실제로 둘 다 호출되는가")
    print("=" * 60)

    hit = 0
    for question in DUAL_NEED_QUESTIONS:
        tools = await _select_tools(question)
        both = "policy_search_tool" in tools and "web_search_tool" in tools
        if both:
            hit += 1
        print(f"  {'OK' if both else 'MISS':4s} {question} -> {tools}")

    print(f"\n재현율: {hit}/{len(DUAL_NEED_QUESTIONS)} ({hit / len(DUAL_NEED_QUESTIONS):.1%})")


# ---------------------------------------------------------------------
# 2) 정밀도: 하나만 필요한 질문에서 괜히 둘 다 부르지 않는가 (회귀 테스트)
# ---------------------------------------------------------------------
SINGLE_NEED_QUESTIONS = [
    ("청년내일저축계좌 지원 대상 알려줘", "policy_search_tool"),
    ("기초생활수급자 신청 방법이 궁금해요", "policy_search_tool"),
    ("청년월세지원 신청할 때 필요한 서류가 뭐예요?", "policy_search_tool"),
    ("2026년 청년 정책 변경된 내용 있어?", "web_search_tool"),
    ("올해 새로 생긴 복지 정책 있나요?", "web_search_tool"),
]


async def test_precision() -> None:
    print("\n" + "=" * 60)
    print("[2] 정밀도: 하나만 필요한 질문에서 불필요하게 여러 tool을 안 부르는가")
    print("=" * 60)

    single_call_count = 0
    for question, expected in SINGLE_NEED_QUESTIONS:
        tools = await _select_tools(question)
        is_single = tools == [expected]
        if is_single:
            single_call_count += 1
        extra = "" if is_single else f"  (기대: [{expected}])"
        print(f"  {'OK' if is_single else 'OVER-CALL':10s} {question} -> {tools}{extra}")

    n = len(SINGLE_NEED_QUESTIONS)
    print(f"\n단일 호출 유지율: {single_call_count}/{n} ({single_call_count / n:.1%})")


# ---------------------------------------------------------------------
# 3) general_response_tool 배타성
# ---------------------------------------------------------------------
GENERAL_QUESTIONS = [
    "오늘 날씨 알려줘",
    "파이썬 공부법 알려줘",
    "복지모니 코드좀 작성해줘",
]


async def test_general_exclusivity() -> None:
    print("\n" + "=" * 60)
    print("[3] general_response_tool 배타성 (다른 tool과 같이 호출되면 안 됨)")
    print("=" * 60)

    ok = 0
    for question in GENERAL_QUESTIONS:
        tools = await _select_tools(question)
        is_exclusive = tools == ["general_response_tool"]
        if is_exclusive:
            ok += 1
        print(f"  {'OK' if is_exclusive else 'FAIL':4s} {question} -> {tools}")

    print(f"\n배타성 유지율: {ok}/{len(GENERAL_QUESTIONS)} ({ok / len(GENERAL_QUESTIONS):.1%})")


# ---------------------------------------------------------------------
# 4) 병렬 실행 확인: 진짜 동시에 도는가 (max에 가까운지, sum에 가까운지)
# ---------------------------------------------------------------------
async def test_parallel_execution() -> None:
    print("\n" + "=" * 60)
    print("[4] 병렬 실행 확인 (순차였다면 sum, 병렬이면 max에 가까워야 함)")
    print("=" * 60)

    question = "청년내일저축계좌 조건이 올해 바뀌었나요?"

    # 각 tool 단독 소요시간
    t0 = time.perf_counter()
    await policy_search_tool.ainvoke({"query": question})
    policy_solo = time.perf_counter() - t0

    t0 = time.perf_counter()
    await web_search_tool.ainvoke({"query": question})
    web_solo = time.perf_counter() - t0

    # tool_executor로 두 tool을 실제로 같이 실행했을 때 소요시간
    state = _new_state(question)
    agent_result = await information_agent(state)
    state["messages"] = state["messages"] + agent_result["messages"]

    next_node = tool_router(state)
    if next_node != "tool_executor":
        print("  두 tool이 선택되지 않아 이 테스트를 건너뜁니다.")
        return

    t0 = time.perf_counter()
    await tool_executor(state)
    combined = time.perf_counter() - t0

    expected_sequential = policy_solo + web_solo
    expected_parallel = max(policy_solo, web_solo)

    print(f"  policy_search_tool 단독: {policy_solo:.2f}s")
    print(f"  web_search_tool 단독   : {web_solo:.2f}s")
    print(f"  순차였다면(sum)        : {expected_sequential:.2f}s")
    print(f"  병렬이었다면(max)      : {expected_parallel:.2f}s")
    print(f"  실제 tool_executor     : {combined:.2f}s")

    if combined <= expected_sequential * 0.8:
        print("  -> 병렬 실행 확인됨 (sum보다 확실히 빠름)")
    else:
        print("  -> 병렬 실행 의심스러움 (sum에 가까움 - 순차 실행처럼 보임)")


# ---------------------------------------------------------------------
# 5) 병합 답변 품질 (정성 평가용 출력 - 직접 읽어보고 판단)
# ---------------------------------------------------------------------
async def test_merged_answer_quality() -> None:
    print("\n" + "=" * 60)
    print("[5] 병합 답변 품질 (정성 평가 - 직접 읽어보고 판단)")
    print("=" * 60)

    for question in DUAL_NEED_QUESTIONS[:1]:
        state = _new_state(question)

        agent_result = await information_agent(state)
        state["messages"] = state["messages"] + agent_result["messages"]

        next_node = tool_router(state)
        if next_node == "tool_executor":
            exec_result = await tool_executor(state)
            state["messages"] = state["messages"] + exec_result["messages"]
            state["context"] = state["context"] + exec_result["context"]
            if "answer" in exec_result:
                state["answer"] = exec_result["answer"]

        if post_tool_router(state) == "generate":
            generate_result = await generate(state)
            state.update(generate_result)

        print(f"\nQ: {question}")
        print(f"context 개수: {len(state['context'])}")
        print(f"\n[최종 답변]\n{state.get('answer', '(없음)')}")


async def main() -> None:
    await test_recall()
    await test_precision()
    await test_general_exclusivity()
    await test_parallel_execution()
    await test_merged_answer_quality()


if __name__ == "__main__":
    asyncio.run(main())
