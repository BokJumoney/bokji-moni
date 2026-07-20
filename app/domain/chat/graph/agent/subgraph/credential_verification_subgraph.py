from langgraph.graph import END, START, StateGraph

from app.domain.chat.graph.agent.nodes.extract_latest_policy import extract_latest_policy
from app.domain.chat.graph.agent.nodes.extract_policy_qualification import extract_policy_qualification
from app.domain.chat.graph.agent.nodes.generate_credential import generate_credential
from app.domain.chat.graph.agent.nodes.router.forms_routers import (
    route_policy_extraction,
    route_credential_background
)
from app.domain.chat.graph.agent.nodes.solid_outputs import (
    user_background_not_found,
    credential_policy_not_found,
    policy_qualification_not_found,
)
from app.domain.chat.graph.agent.states.credential_state import CredentialState

builder = StateGraph(
    CredentialState
)

builder.add_node("extract_latest_policy", extract_latest_policy)
builder.add_node("extract_policy_qualification", extract_policy_qualification)
builder.add_node("credential_policy_not_found", credential_policy_not_found)
builder.add_node("policy_qualification_not_found", policy_qualification_not_found)
builder.add_node("user_background_not_found", user_background_not_found)
builder.add_node("generate_credential", generate_credential)

builder.add_edge(START, "extract_latest_policy")

builder.add_conditional_edges(
    "extract_latest_policy",
    route_policy_extraction,
    {
        "policy_found": "extract_policy_qualification",
        "policy_not_found": "credential_policy_not_found",
    },
)

builder.add_conditional_edges(
    "extract_policy_qualification",
    route_credential_background,
    {
        "credential_background_found": "generate_credential",
        "credential_not_found": "policy_qualification_not_found",
        "user_background_not_found": "user_background_not_found",
    },
)


builder.add_edge("credential_policy_not_found", END)
builder.add_edge("policy_qualification_not_found", END)
builder.add_edge("user_background_not_found", END)
builder.add_edge("generate_credential", END)

credential_verification_subgraph = builder.compile()

