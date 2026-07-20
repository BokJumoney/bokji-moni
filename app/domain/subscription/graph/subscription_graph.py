"""정책 구독 요청을 독립적으로 처리하는 LangGraph 서브그래프."""

from langgraph.graph import END, START, StateGraph

from app.domain.subscription.graph.nodes import (
    execute_subscription_tool,
    route_after_tool_selection,
    select_subscription_tool,
)
from app.domain.subscription.graph.state import (
    SubscriptionGraphInput,
    SubscriptionGraphOutput,
    SubscriptionGraphState,
)


def build_subscription_graph():
    """부모 그래프에 중첩할 수 있는 컴파일된 구독 그래프를 만든다."""
    builder = StateGraph(
        SubscriptionGraphState,
        input_schema=SubscriptionGraphInput,
        output_schema=SubscriptionGraphOutput,
    )
    builder.add_node("select_tool", select_subscription_tool)
    builder.add_node("execute_tool", execute_subscription_tool)
    builder.add_edge(START, "select_tool")
    builder.add_conditional_edges(
        "select_tool",
        route_after_tool_selection,
        {
            "execute_tool": "execute_tool",
            "end": END,
        },
    )
    builder.add_edge("execute_tool", END)
    return builder.compile()


# 부모 그래프는 내부 실행 함수를 직접 등록하지 않고 이 컴파일된 그래프만 사용한다.
subscription_graph = build_subscription_graph()
