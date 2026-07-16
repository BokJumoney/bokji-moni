"""정책 구독 대화를 처리하는 LangGraph 서브그래프."""

from langgraph.graph import END, START, StateGraph

from app.domain.chat.graph.nodes.subscription.agent import subscription_agent
from app.domain.chat.graph.state import ChatGraphState


workflow = StateGraph(ChatGraphState)

# 노드 생성
workflow.add_node("subscription_agent", subscription_agent)

# 엣지 생성
workflow.add_edge(START, "subscription_agent")
workflow.add_edge("subscription_agent", END)

subscription_graph = workflow.compile()
