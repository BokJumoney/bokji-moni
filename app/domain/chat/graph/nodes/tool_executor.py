"""
Tool Executor.

information_agent가 선택한 tool_call(들)을 실제로 실행하고,
결과를 ToolMessage로 state.messages에 추가한다. 동시에 결과 텍스트를
state.context에도 모아서 Answer Generator(generate.py)가 바로
사용할 수 있게 한다.

예외: general_response_tool만 호출된 경우엔 이미 정해진 고정 안내
문구이므로, generate(LLM 재작성)를 거치지 않고 그 문구를 그대로
state.answer로 확정한다. (그렇지 않으면 generate의 "문서가 없으면
일반 지식으로 답변" 폴백 때문에 GPT가 날씨/코딩 같은 무관한 질문에
일반 지식으로 답해버릴 수 있음 - general_response_tool의 존재 의미가
없어짐)
"""

import asyncio

from langchain_core.messages import ToolMessage

from app.domain.chat.graph.state2 import ChatState
from app.domain.chat.graph.tools.policy_search import policy_search_tool
from app.domain.chat.graph.tools.web_search import web_search_tool
from app.domain.chat.graph.tools.general_response import general_response_tool

_TOOL_MAP = {
    policy_search_tool.name: policy_search_tool,
    web_search_tool.name: web_search_tool,
    general_response_tool.name: general_response_tool,
}


async def tool_executor(state: ChatState) -> dict:
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls

    async def run(call: dict):
        tool_fn = _TOOL_MAP[call["name"]]
        result = await tool_fn.ainvoke(call["args"])
        message = ToolMessage(
            content=result,
            tool_call_id=call["id"],
            name=call["name"],
        )
        return message, result

    # asyncio - 여러 비동기 작업을 동시에 실행하는 역할
    # policy_search , web_search 동시 시작
    outcomes = await asyncio.gather(*(run(call) for call in tool_calls))

    for call, (_, result) in zip(tool_calls, outcomes):
        print(f"------ TOOL RESULT [{call['name']}] ------")
        print(f"args: {call['args']}")
        print(result)
        print("------------------------------------------")

    update = {
        "messages": [outcome[0] for outcome in outcomes],
        "context": [outcome[1] for outcome in outcomes],
    }

    is_general_only = (
        len(tool_calls) == 1 and tool_calls[0]["name"] == general_response_tool.name
    )
    if is_general_only:
        update["answer"] = outcomes[0][1]

    return update
