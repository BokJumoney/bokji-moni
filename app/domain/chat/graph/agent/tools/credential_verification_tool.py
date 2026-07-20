from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from app.domain.chat.graph.agent.states.credential_state import CredentialState
from app.domain.chat.graph.agent.subgraph.credential_verification_subgraph import credential_verification_subgraph


def _messages_from_config(query: str, config: RunnableConfig) -> list:
    messages = config.get("configurable", {}).get("messages")
    return list(messages) if messages else [HumanMessage(content=query)]


@tool
async def credential_verification_tool(query: str, config: RunnableConfig) -> dict:
    """로그인 사용자의 상세 정보와 정책 자격 요건을 비교해 신청 가능성을 판정합니다."""
    user_id = config.get("configurable", {}).get("user_id")
    if user_id is None:
        return {"answer": "로그인 사용자 정보가 없어 신청 자격을 확인할 수 없습니다."}

    child_input: CredentialState = {
        "messages": _messages_from_config(query, config),
        "user_id": user_id,
    }
    result = await credential_verification_subgraph.ainvoke(child_input)
    answer = result.get("answer") or result.get("error_message")

    return {
        "answer": answer or "신청 자격을 확인하지 못했습니다.",
    }
