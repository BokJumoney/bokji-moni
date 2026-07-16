"""정책 구독 대화를 처리하는 LangGraph 서브그래프."""

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.domain.chat.graph.nodes.subscription.agent import (
    SUBSCRIPTION_TOOLS,
    finalize_subscription_tool,
    handle_active_subscription,
    route_tool_call,
    subscription_entry,
    subscription_tool_agent,
    subscription_tool_fallback,
)
from app.domain.chat.graph.state import ChatGraphState


workflow = StateGraph(ChatGraphState)

# 진행 중인 확인 대화는 LLM을 건너뛰고, 신규 요청만 도구를 선택한다.
workflow.add_node("subscription_entry", subscription_entry)
workflow.add_node("active_subscription", handle_active_subscription)
workflow.add_node("subscription_tool_agent", subscription_tool_agent)
workflow.add_node("subscription_tools", ToolNode(SUBSCRIPTION_TOOLS))
workflow.add_node("finalize_subscription_tool", finalize_subscription_tool)
workflow.add_node("subscription_tool_fallback", subscription_tool_fallback)

workflow.add_edge(START, "subscription_entry")
workflow.add_conditional_edges(
    "subscription_entry",
    lambda state: state["subscription_stage"],
    {
        "active": "active_subscription",
        "new": "subscription_tool_agent",
    },
)
workflow.add_edge("active_subscription", END)
workflow.add_conditional_edges(
    "subscription_tool_agent",
    route_tool_call,
    {
        "tools": "subscription_tools",
        "fallback": "subscription_tool_fallback",
    },
)
workflow.add_edge("subscription_tools", "finalize_subscription_tool")
workflow.add_edge("finalize_subscription_tool", END)
workflow.add_edge("subscription_tool_fallback", END)

subscription_graph = workflow.compile()
