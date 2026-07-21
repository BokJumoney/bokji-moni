from app.domain.chat.graph.agent.states.search_form_state import SearchFormState


async def search_forms(state: SearchFormState) -> SearchFormState:
    """
    복지 정책 신청을 위한 신청서 혹은 구비서류를 원할 경우 사용합니다.
    서류를 찾고 사용자에게 다운로드 링크를 제공하는 기능을 수행합니다.
    """
    from app.domain.chat.graph.agent.subgraph.seach_form_subgraph import search_form_subgraph

    child_input: SearchFormState = {
        "messages": state.get("messages", []),
    }

    result = await search_form_subgraph.ainvoke(child_input)

    return result