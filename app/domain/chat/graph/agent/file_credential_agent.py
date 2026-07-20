from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.domain.chat.graph.agent.tools import FILE_CREDENTIAL_TOOLS
from app.domain.chat.graph.state2 import ChatState
from app.infrastructure.llm.gpt import get_llm_gpt


SYSTEM_PROMPT = """당신은 복지 정책 서비스의 신청서·자격 확인 도구 선택 에이전트입니다.
사용자 요청을 보고 아래 도구 중 정확히 하나만 호출하세요. 직접 답변하지 마세요.

1. search_form_tool
   실제 신청서, 서식, 양식, 구비서류 파일 또는 다운로드 링크를 요청할 때 사용합니다.

2. credential_verification_tool
   사용자가 자신의 소득·나이·가구·재산 등 상세 정보가 특정 정책의 자격 요건을
   충족하는지, 본인이 신청 대상인지 확인해 달라고 할 때 사용합니다.

현재 요청을 query 인자에 그대로 전달하세요."""

_TOOL_MAP = {registered_tool.name: registered_tool for registered_tool in FILE_CREDENTIAL_TOOLS}
_llm_with_tools = get_llm_gpt().bind_tools(
    FILE_CREDENTIAL_TOOLS,
    tool_choice="required",
)


def _conversation_messages(state: ChatState) -> list[BaseMessage]:
    converted: list[BaseMessage] = []
    for message in state.get("messages", []):
        if isinstance(message, BaseMessage):
            converted.append(message)
            continue
        if not isinstance(message, dict):
            continue

        content = str(message.get("content", ""))
        role = message.get("role") or message.get("type")
        if role in {"user", "human"}:
            converted.append(HumanMessage(content=content))
        elif role in {"assistant", "ai"}:
            converted.append(AIMessage(content=content))

    question = str(state.get("question") or "").strip()
    latest_human = next(
        (message for message in reversed(converted) if isinstance(message, HumanMessage)),
        None,
    )
    if question and (latest_human is None or latest_human.content != question):
        converted.append(HumanMessage(content=question))
    return converted or [HumanMessage(content=question)]


def _fallback_tool_name(question: str) -> str:
    credential_keywords = (
        "자격",
        "대상",
        "신청 가능",
        "받을 수",
        "해당되",
        "조건 충족",
    )
    if any(keyword in question for keyword in credential_keywords):
        return "credential_verification_tool"
    return "search_form_tool"


async def file_credential_agent(state: ChatState) -> dict:
    """신청서 제공 또는 신청 자격 확인 tool을 선택해 실행한다."""
    conversation = _conversation_messages(state)
    response = await _llm_with_tools.ainvoke(
        [SystemMessage(content=SYSTEM_PROMPT), *conversation]
    )

    question = str(state.get("question") or conversation[-1].content)
    if response.tool_calls:
        tool_call = response.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = dict(tool_call.get("args", {}))
    else:
        tool_name = _fallback_tool_name(question)
        tool_args = {}

    selected_tool = _TOOL_MAP.get(tool_name)
    if selected_tool is None:
        return {
            "answer": "신청서 제공 또는 신청 자격 확인 요청인지 확인하지 못했습니다.",
            "files": [],
        }

    tool_args["query"] = tool_args.get("query") or question
    result = await selected_tool.ainvoke(
        tool_args,
        config={
            "configurable": {
                "messages": conversation,
                "user_id": state.get("user_id"),
            }
        },
    )
    if not isinstance(result, dict):
        return {"answer": str(result), "files": []}

    return {
        "answer": result.get("answer") or "요청을 처리하지 못했습니다.",
        "files": result.get("files", []),
    }
