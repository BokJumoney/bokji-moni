"""
파이프라인 구간별 Latency 측정 스크립트.

information_agent(tool 선택 LLM 호출 1회) -> tool_executor(DB 쿼리 병렬 /
Tavily 호출) -> generate(답변 생성 LLM 호출 1회, general_response_tool인
경우엔 건너뜀) 각 단계 소요 시간을 time.perf_counter()로 재서 어디가
병목인지 확인한다.

실행:
    python -m app.test_latency
"""

import asyncio
import time
from dataclasses import dataclass, field

from app.domain.chat.graph.nodes.information_agent import information_agent
from app.domain.chat.graph.nodes.tool_executor import tool_executor
from app.domain.chat.graph.router.tool_router import tool_router
from app.domain.chat.graph.router.post_tool_router import post_tool_router
from app.domain.chat.graph.nodes.generate import generate

TEST_QUESTIONS = [
    ("policy", "청년내일저축계좌 지원 대상 알려줘"),
    ("freshness", "2026년 청년 정책 변경된 내용 있어?"),
    ("general", "오늘 날씨 알려줘"),
]


@dataclass
class Timing:
    question: str
    category: str
    tool_selected: list = field(default_factory=list)
    information_agent_sec: float = 0.0
    tool_executor_sec: float = 0.0
    generate_sec: float = 0.0
    total_sec: float = 0.0
    generate_skipped: bool = False


def _new_state(question: str) -> dict:
    return {
        "question": question,
        "intent": "",
        "messages": [],
        "context": [],
        "answer": "",
    }


async def measure(category: str, question: str) -> Timing:
    timing = Timing(question=question, category=category)
    state = _new_state(question)

    total_start = time.perf_counter()

    # 1) Agent: tool 선택
    t0 = time.perf_counter()
    agent_result = await information_agent(state)
    timing.information_agent_sec = time.perf_counter() - t0
    state["messages"] = state["messages"] + agent_result["messages"]

    timing.tool_selected = [
        call["name"]
        for call in (getattr(agent_result["messages"][0], "tool_calls", None) or [])
    ]

    next_node = tool_router(state)

    # 2) tool 실행 (DB 쿼리 병렬 / Tavily 호출 / 고정 문구 생성)
    if next_node == "tool_executor":
        t0 = time.perf_counter()
        exec_result = await tool_executor(state)
        timing.tool_executor_sec = time.perf_counter() - t0

        state["messages"] = state["messages"] + exec_result["messages"]
        state["context"] = state["context"] + exec_result["context"]
        if "answer" in exec_result:
            state["answer"] = exec_result["answer"]

    # 3) 답변 생성 (general_response_tool만 쓰인 경우엔 건너뜀)
    if post_tool_router(state) == "generate":
        t0 = time.perf_counter()
        generate_result = await generate(state)
        timing.generate_sec = time.perf_counter() - t0
        state.update(generate_result)
    else:
        timing.generate_skipped = True

    timing.total_sec = time.perf_counter() - total_start
    return timing


def _print_timing(timing: Timing) -> None:
    print(f"\nQ [{timing.category}]: {timing.question}")
    print(f"  선택된 tool        : {timing.tool_selected}")
    print(f"  information_agent  : {timing.information_agent_sec:6.3f}s")
    if timing.tool_executor_sec:
        print(f"  tool_executor      : {timing.tool_executor_sec:6.3f}s")
    if timing.generate_skipped:
        print("  generate           : 건너뜀 (general_response_tool)")
    else:
        print(f"  generate           : {timing.generate_sec:6.3f}s")
    print("  ------------------------------")
    print(f"  총 소요 시간        : {timing.total_sec:6.3f}s")


def _print_summary(timings: list) -> None:
    print(f"\n{'=' * 60}")
    print("=== 요약 (평균) ===")

    n = len(timings)
    avg_agent = sum(t.information_agent_sec for t in timings) / n
    avg_total = sum(t.total_sec for t in timings) / n

    executor_times = [t.tool_executor_sec for t in timings if t.tool_executor_sec]
    generate_times = [t.generate_sec for t in timings if not t.generate_skipped]

    print(f"  information_agent 평균 : {avg_agent:.3f}s  ({n}건)")
    if executor_times:
        print(
            f"  tool_executor 평균     : {sum(executor_times) / len(executor_times):.3f}s"
            f"  ({len(executor_times)}건)"
        )
    if generate_times:
        print(
            f"  generate 평균          : {sum(generate_times) / len(generate_times):.3f}s"
            f"  ({len(generate_times)}건)"
        )
    print(f"  전체 평균              : {avg_total:.3f}s")

    llm_call_questions = [t for t in timings if not t.generate_skipped]
    if llm_call_questions:
        avg_llm_ratio = sum(
            (t.information_agent_sec + t.generate_sec) / t.total_sec
            for t in llm_call_questions
        ) / len(llm_call_questions)
        print(f"  LLM 호출(tool선택+답변생성) 비중 평균: {avg_llm_ratio:.1%}")


async def main() -> None:
    timings = []
    for category, question in TEST_QUESTIONS:
        timing = await measure(category, question)
        _print_timing(timing)
        timings.append(timing)

    _print_summary(timings)


if __name__ == "__main__":
    asyncio.run(main())