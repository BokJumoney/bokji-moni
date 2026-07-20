"""
post_tool_router 도입 전/후 속도 비교 벤치마크.

측정 대상: 복지 무관 질문 (general_response_tool만 호출되는 케이스)
  - AFTER  (지금 구조): tool_executor -> post_tool_router가 "end"로 보내서 generate 스킵
  - BEFORE (예전 구조 시뮬레이션): post_tool_router 없이 무조건 generate까지 호출

※ 정책 관련 질문(policy_search_tool 등)은 어차피 두 경우 다 generate를 거치므로
  차이가 없다. 이 벤치마크는 "복지와 무관한 질문"에서만 의미가 있다.

실행:
    python benchmark_post_tool_router.py
"""
import asyncio
import statistics
import time

from app.domain.chat.graph.nodes.generate import generate
from app.domain.chat.graph.nodes.information_agent import information_agent
from app.domain.chat.graph.nodes.tool_executor import tool_executor
from app.domain.chat.graph.chat_graph import graph as graph_after
from app.domain.chat.graph.state2 import ChatState
from app.domain.chat.graph.nodes.intent_router import intent_router  # 실제 함수명/경로 확인 필요


# 복지와 무관한 질문들 (general_response_tool만 호출될 것으로 기대되는 케이스)
TEST_QUESTIONS = [
    "오늘 날씨 알려줘",
    "주식 투자 어떻게 시작해?",
    "복지모니 코드좀 작성해줘",
    "돈 많이 버는 법 알려줘",
    "파이썬 공부법 알려줘",
]

N_TRIALS = 3  # 질문마다 반복 횟수 (평균을 내기 위함 - 네트워크/LLM 응답 편차 완화)


async def run_after(question: str) -> float:
    """지금 구조 그대로 실행. post_tool_router가 generate를 알아서 스킵해줌."""
    start = time.perf_counter()
    await graph_after.ainvoke({"question": question})
    return time.perf_counter() - start




async def run_before(question: str) -> float:
    """예전 구조 재현: intent_router까지는 AFTER와 동일하게 거치고,
    post_tool_router 분기 없이 generate까지 무조건 호출한다."""
    start = time.perf_counter()

    state: ChatState = {"question": question}  # type: ignore[typeddict-item]

    # AFTER와 동일한 경로 재현 (여기가 빠져 있던 부분)
    intent_result = await intent_router(state)
    state = {**state, **intent_result}

    agent_result = await information_agent(state)
    state = {**state, **agent_result}

    tool_result = await tool_executor(state)
    state = {**state, **tool_result}

    # post_tool_router의 분기 없이 무조건 generate까지 실행 (예전 동작 재현)
    await generate(state)

    return time.perf_counter() - start


async def main():
    header = f"{'질문':28s} | {'AFTER(초)':>9s} | {'BEFORE(초)':>10s} | {'절감(초)':>8s} | {'절감율':>7s}"
    print(header)
    print("-" * len(header))

    after_times: list[float] = []
    before_times: list[float] = []

    for q in TEST_QUESTIONS:
        after_trials = [await run_after(q) for _ in range(N_TRIALS)]
        before_trials = [await run_before(q) for _ in range(N_TRIALS)]

        after_avg = statistics.mean(after_trials)
        before_avg = statistics.mean(before_trials)
        saved = before_avg - after_avg
        pct = (saved / before_avg * 100) if before_avg else 0.0

        after_times.append(after_avg)
        before_times.append(before_avg)

        print(f"{q[:26]:28s} | {after_avg:9.2f} | {before_avg:10.2f} | {saved:8.2f} | {pct:6.1f}%")

    print("-" * len(header))
    overall_after = statistics.mean(after_times)
    overall_before = statistics.mean(before_times)
    overall_saved = overall_before - overall_after
    overall_pct = (overall_saved / overall_before * 100) if overall_before else 0.0
    print(
        f"{'전체 평균':28s} | {overall_after:9.2f} | {overall_before:10.2f} "
        f"| {overall_saved:8.2f} | {overall_pct:6.1f}%"
    )


if __name__ == "__main__":
    asyncio.run(main())
