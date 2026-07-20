from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from app.domain.chat.graph.agent.subgraph.seach_form_subgraph import search_form_subgraph
from app.domain.chat.graph.agent.states.search_form_state import SearchFormState


def _messages_from_config(query: str, config: RunnableConfig) -> list:
    messages = config.get("configurable", {}).get("messages")
    return list(messages) if messages else [HumanMessage(content=query)]

@tool
async def search_form_tool(query: str, config: RunnableConfig) -> dict:
    """복지 정책의 실제 신청서·서식 파일과 다운로드 링크를 찾습니다."""
    child_input: SearchFormState = {
        "messages": _messages_from_config(query, config),
    }
    result = await search_form_subgraph.ainvoke(child_input)
    forms = result.get("forms", [])

    if forms:
        policy_name = result.get("policy_name") or "해당 정책"
        answer = f"{policy_name} 신청서를 찾았습니다. 아래 파일을 내려받아 주세요."
    else:
        answer = result.get("error_message") or "신청서를 찾지 못했습니다."

    return {"answer": answer, "files": forms}
