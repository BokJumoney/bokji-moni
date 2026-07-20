from langgraph.graph import StateGraph, START, END
from app.domain.chat.graph.agent.states.search_form_state import SearchFormState
from app.domain.chat.graph.agent.nodes.solid_outputs import policy_not_found_in_state, policy_id_not_found_in_state, policy_forms_not_found_in_state
from app.domain.chat.graph.agent.nodes.extract_latest_policy import extract_latest_policy
from app.domain.chat.graph.agent.nodes.extract_policy_id import extract_policy_id
from app.domain.chat.graph.agent.nodes.router.forms_routers import route_policy_extraction, route_policy_id_extraction
from app.domain.chat.graph.agent.nodes.search_forms_by_id import search_forms_by_id

builder = StateGraph(
    SearchFormState
)

builder.add_node("extract_latest_policy", extract_latest_policy)
builder.add_node("policy_not_found_in_state", policy_not_found_in_state)
builder.add_node("extract_policy_id", extract_policy_id)
builder.add_node("search_forms_by_id", search_forms_by_id)
builder.add_node("policy_id_not_found_in_state", policy_id_not_found_in_state)
builder.add_node("policy_forms_not_found_in_state", policy_forms_not_found_in_state)

# 조건부 node 추가
builder.add_conditional_edges(
    "extract_latest_policy",
    route_policy_extraction,
    {
        "policy_found": "extract_policy_id",
        "policy_not_found": "policy_not_found_in_state",
    }
)

builder.add_conditional_edges(
    "extract_policy_id",
    route_policy_id_extraction,
    {
        "policy_id_found": "search_forms_by_id",
        "policy_id_not_found": "policy_id_not_found_in_state"
    }
)

builder.add_conditional_edges(
    "search_forms_by_id",
    lambda state: (
        "forms_found"
        if state.get("forms")
        else "forms_not_found"
    ),
    {
        "forms_found": END,
        "forms_not_found": "policy_forms_not_found_in_state",
    },
)

builder.add_edge(START, "extract_latest_policy")
builder.add_edge("policy_not_found_in_state", END)
builder.add_edge("policy_id_not_found_in_state", END)
builder.add_edge("policy_forms_not_found_in_state", END)

search_form_subgraph = builder.compile()
