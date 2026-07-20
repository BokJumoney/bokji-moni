from app.rag.policy_retriever import search_policy_info
from app.domain.chat.graph.agent.states.search_form_state import SearchFormState


def _normalize(value: str) -> str:
    return "".join(value.lower().split())

async def extract_policy_id(search_form_state: SearchFormState) -> dict:
    policy_name = (search_form_state.get("policy_name") or "").strip()
    if not policy_name:
        return {"service_id": None}

    docs = await search_policy_info(f"{policy_name} 기본정보", 5)
    candidates: list[tuple[str, str]] = []
    seen: set[str] = set()
    for doc in docs:
        service_id = str(doc.metadata.get("service_id", "")).strip()
        service_name = str(doc.metadata.get("service_name", "")).strip()
        if service_id and service_id not in seen:
            seen.add(service_id)
            candidates.append((service_id, service_name))

    if not candidates:
        return {"service_id": None}

    normalized_query = _normalize(policy_name)
    matched = next(
        (
            candidate
            for candidate in candidates
            if candidate[1]
            and (
                normalized_query == _normalize(candidate[1])
                or normalized_query in _normalize(candidate[1])
                or _normalize(candidate[1]) in normalized_query
            )
        ),
        candidates[0],
    )
    return {"service_id": matched[0], "policy_name": matched[1] or policy_name}
