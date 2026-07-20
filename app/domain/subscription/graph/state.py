"""부모 채팅 그래프와 경계를 이루는 구독 서브그래프 상태."""

from typing import Any, NotRequired, TypedDict


class SubscriptionGraphInput(TypedDict):
    """부모 채팅 그래프에서 구독 서브그래프로 들어오는 값."""

    question: str


class SubscriptionGraphOutput(TypedDict):
    """구독 서브그래프가 부모 채팅 그래프로 돌려주는 값."""

    answer: str


class SubscriptionGraphState(TypedDict):
    """구독 서브그래프가 부모와 공유하는 최소 상태.

    ``question``과 ``answer``만 부모 ``ChatState``와 공유한다. 인증 식별자는
    상태에 저장하지 않고 RunnableConfig로 전달해 모델 입력과 분리한다.
    """

    question: str
    answer: NotRequired[str]
    # 아래 두 값은 서브그래프 내부 노드 사이에서만 전달되며 부모 ChatState에는
    # 병합되지 않는다.
    selected_tool_name: NotRequired[str | None]
    selected_tool_args: NotRequired[dict[str, Any]]
