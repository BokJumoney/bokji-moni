"""구독 서브그래프의 Tool 선택·실행 노드와 분기 함수.

첫 노드는 LLM이 요청에 맞는 Tool 하나를 선택하게 하고, 두 번째 노드는
선택된 Tool을 실제로 실행한다. 질문은 그래프 상태에서 읽지만 데이터 접근
권한은 모델 입력이 아닌 RunnableConfig의 인증 컨텍스트에서만 가져온다.
"""

import logging
import uuid
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool

from app.domain.subscription.graph.prompts import SUBSCRIPTION_TOOL_PROMPT
from app.domain.subscription.graph.schemas import SubscriptionExecutionContext
from app.domain.subscription.graph.state import SubscriptionGraphState
from app.domain.subscription.graph.tools import build_subscription_tools
from app.infrastructure.llm.gpt import get_llm_gpt

logger = logging.getLogger(__name__)


def _execution_context(
    config: RunnableConfig,
) -> SubscriptionExecutionContext | None:
    """서버가 전달한 인증 식별자를 검증해 Tool 실행 컨텍스트로 바꾼다.

    값이 없거나 UUID 형식이 아니면 임의 기본 사용자를 선택하지 않고
    ``None``을 반환해 개인 데이터 접근을 닫힌 상태로 실패시킨다.
    """
    configurable = config.get("configurable", {})
    raw_user_id = configurable.get("user_id")
    if raw_user_id is None:
        return None
    try:
        return SubscriptionExecutionContext(user_id=uuid.UUID(str(raw_user_id)))
    except (TypeError, ValueError):
        return None


def _request_tools(config: RunnableConfig) -> list[BaseTool] | None:
    """인증 컨텍스트가 유효할 때만 사용자 범위가 고정된 Tool을 만든다."""
    context = _execution_context(config)
    if context is None:
        return None
    return build_subscription_tools(context)


async def select_subscription_tool(
    state: SubscriptionGraphState,
    config: RunnableConfig,
) -> dict[str, object]:
    """LLM Tool Calling으로 현재 요청에서 실행할 Tool 하나를 선택한다."""
    tools = _request_tools(config)
    if tools is None:
        return {
            "answer": "구독 요청을 처리하려면 로그인된 사용자 정보가 필요합니다.",
            "selected_tool_name": None,
            "selected_tool_args": {},
        }
    if not tools:
        return {
            "answer": "현재 구독 요청을 처리할 수 없습니다.",
            "selected_tool_name": None,
            "selected_tool_args": {},
        }

    # required는 설정·목록 같은 읽기 요청에도 실제 Tool 선택을 강제한다.
    tool_map = {tool.name: tool for tool in tools}
    llm_with_tools = get_llm_gpt().bind_tools(
        tools,
        tool_choice="required",
    )
    response = await llm_with_tools.ainvoke(
        [
            SystemMessage(content=SUBSCRIPTION_TOOL_PROMPT),
            HumanMessage(content=state["question"]),
        ]
    )
    tool_calls = list(getattr(response, "tool_calls", None) or [])
    # 여러 변경이 일부만 성공하지 않도록 한 요청에서 정확히 하나만 허용한다.
    if len(tool_calls) != 1:
        return {
            "answer": "한 번에 하나의 구독 요청만 처리할 수 있습니다. 요청을 하나씩 알려주세요.",
            "selected_tool_name": None,
            "selected_tool_args": {},
        }

    call = tool_calls[0]
    tool_name = call.get("name", "")
    tool_args = call.get("args", {})
    if tool_name not in tool_map or not isinstance(tool_args, dict):
        return {
            "answer": "현재 단계에서 실행할 수 없는 구독 요청입니다.",
            "selected_tool_name": None,
            "selected_tool_args": {},
        }
    return {
        "selected_tool_name": tool_name,
        "selected_tool_args": tool_args,
    }


def route_after_tool_selection(
    state: SubscriptionGraphState,
) -> Literal["execute_tool", "end"]:
    """유효한 Tool이 선택됐을 때만 실행 노드로 이동한다."""
    if state.get("selected_tool_name"):
        return "execute_tool"
    return "end"


async def execute_subscription_tool(
    state: SubscriptionGraphState,
    config: RunnableConfig,
) -> dict[str, str]:
    """선택된 허용 Tool을 실행하고 그 결과를 최종 답변으로 반환한다."""
    tools = _request_tools(config)
    if tools is None:
        return {
            "answer": "구독 요청을 처리하려면 로그인된 사용자 정보가 필요합니다."
        }

    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get(state.get("selected_tool_name", ""))
    if tool is None:
        return {"answer": "현재 단계에서 실행할 수 없는 구독 요청입니다."}

    try:
        result = await tool.ainvoke(state.get("selected_tool_args", {}))
    except Exception:  # noqa: BLE001
        logger.exception("구독 Tool 실행 실패: tool=%s", tool.name)
        return {
            "answer": "구독 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."
        }

    # Tool의 확정 결과를 그대로 써서 LLM의 재해석이나 값 왜곡을 막는다.
    if isinstance(result, str) and result.strip():
        return {"answer": result.strip()}
    return {"answer": "구독 요청을 처리하지 못했습니다. 입력을 확인해 주세요."}
