from app.domain.chat.graph.agent.states.credential_state import CredentialState
from app.domain.chat.graph.agent.states.search_form_state import SearchFormState


def route_policy_extraction(state: SearchFormState | CredentialState) -> str:
    policy_name = state.get("policy_name")

    if policy_name:
        return "policy_found"

    return "policy_not_found"

def route_policy_id_extraction(state: SearchFormState) -> str:
    service_id = state.get("service_id")

    if service_id:
        return "policy_id_found"
    return "policy_id_not_found"

def route_credential_extraction(state: CredentialState) -> str:
    if state.get("credential"):
        return "credential_found"
    return "credential_not_found"

def route_background_extraction(state: CredentialState) -> str:
    user_background = state.get("user_background")

    if user_background:
        return "user_background_found"
    return "user_background_not_found"

