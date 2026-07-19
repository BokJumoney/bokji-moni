"""구독 노드 안에서 한 번만 실행되는 제한된 Tool Calling 루프.

구독 조회도 모델의 일반 지식으로 답하지 않고 반드시 실제 Tool을 실행한다.
Tool 결과를 다시 모델에게 생성시키지 않아 조회값·변경 결과가 왜곡되는
경로도 차단한다.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.domain.subscription.agent.prompts import SUBSCRIPTION_TOOL_PROMPT
from app.infrastructure.llm.gpt import get_llm_gpt

logger = logging.getLogger(__name__)


class SubscriptionToolLoop:
    """한 요청에서 정확히 하나의 허용된 구독 Tool만 실행한다."""

    async def run(self, question: str, tools: list[BaseTool]) -> str:
        """모델에게 Tool을 고르게 하고 검증된 한 번의 호출 결과를 반환한다."""
        if not tools:
            return "현재 구독 요청을 처리할 수 없습니다."

        # 전달받은 요청 전용 Tool만 이름으로 찾아 실행할 수 있도록 제한한다.
        tool_map = {tool.name: tool for tool in tools}
        # required는 목록·설정 같은 읽기 요청에도 실제 DB Tool 호출을 강제한다.
        llm_with_tools = get_llm_gpt().bind_tools(
            tools,
            tool_choice="required",
        )
        response = await llm_with_tools.ainvoke(
            [
                SystemMessage(content=SUBSCRIPTION_TOOL_PROMPT),
                HumanMessage(content=question),
            ]
        )
        tool_calls = list(getattr(response, "tool_calls", None) or [])
        # 여러 변경을 한 응답에 묶어 일부만 성공하는 상황을 허용하지 않는다.
        if len(tool_calls) != 1:
            return "한 번에 하나의 구독 요청만 처리할 수 있습니다. 요청을 하나씩 알려주세요."

        call = tool_calls[0]
        tool = tool_map.get(call.get("name", ""))
        if tool is None:
            return "현재 단계에서 실행할 수 없는 구독 요청입니다."

        try:
            result = await tool.ainvoke(call.get("args", {}))
        except Exception:  # noqa: BLE001
            logger.exception("구독 Tool 실행 실패: tool=%s", tool.name)
            return "구독 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."

        # Tool의 확정 결과를 그대로 최종 답변으로 써서 LLM의 재해석을 거치지 않는다.
        if isinstance(result, str) and result.strip():
            return result.strip()
        return "구독 요청을 처리하지 못했습니다. 입력을 확인해 주세요."
