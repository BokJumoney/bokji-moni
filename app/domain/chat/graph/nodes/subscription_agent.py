"""정책 구독 요청을 처리하는 전용 Tool Calling 노드.

질문은 ChatState에서 읽지만, 데이터 접근 권한은 모델 입력이 아닌
RunnableConfig의 서버 검증 컨텍스트에서만 가져온다.
"""

import uuid

from langchain_core.runnables import RunnableConfig

from app.domain.chat.graph.state2 import ChatState
from app.domain.subscription.agent.schemas import SubscriptionExecutionContext
from app.domain.subscription.agent.tool_loop import SubscriptionToolLoop
from app.domain.subscription.agent.tools import build_subscription_tools


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


async def subscription_agent(
    state: ChatState,
    config: RunnableConfig,
) -> dict:
    """인증 범위가 고정된 Tool로 구독 의도 하나를 처리한다."""
    context = _execution_context(config)
    if context is None:
        return {
            "answer": "구독 요청을 처리하려면 로그인된 사용자 정보가 필요합니다."
        }

    # Tool factory가 user_id를 클로저에 고정하므로 모델에는 사용자 ID가 보이지 않는다.
    tools = build_subscription_tools(context)
    answer = await SubscriptionToolLoop().run(state["question"], tools)
    return {"answer": answer}
