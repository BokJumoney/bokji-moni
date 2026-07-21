"""
Agent (Tool 선택).

Intent Router가 "정보 조회 / 자격 요건 판단" 계열 질문으로 분류한 뒤
호출되는 노드.

  1. policy_search_tool          - 복지 정책 자체에 대한 질문
  2. web_search_tool             - 최신성이 필요하거나 정보가 부족한 질문
  3. general_response_tool       - 복지 정책과 무관한 질문
  4. welfare_recommendation_tool - 사용자 개인 정보 기반 맞춤 복지 추천 요청
     (실제 실행되지 않는 분류용 스키마. LLM이 이걸 고르면 이 노드가
      직접 가로챈다.)

welfare_recommendation_tool이 선택되면:
  - 배경정보 없음 → 마이페이지 안내 메시지로 즉시 종료
  - 배경정보 있음 → 배경정보로 보강한 쿼리를 만들어 policy_search_tool을
    직접 호출하는 tool_call을 합성해서 정상 파이프라인
    (tool_router → tool_executor → generate)으로 흘려보낸다.
"""
import uuid

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from app.infrastructure.config import settings
from app.domain.chat.graph.state2 import ChatState
from app.domain.chat.graph.tools.policy_search import policy_search_tool
from app.domain.chat.graph.tools.web_search import web_search_tool
from app.domain.chat.graph.tools.general_response import general_response_tool
from app.domain.chat.graph.tools.welfare_recommendation import welfare_recommendation_tool
from app.domain.chat.graph.utils.welfare_check import (
    is_background_complete,
    PROFILE_REQUIRED_MESSAGE,
)

TOOLS = [policy_search_tool, web_search_tool, general_response_tool, welfare_recommendation_tool]

_llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY, temperature=0)
_llm_with_tools = _llm.bind_tools(TOOLS)

SYSTEM_PROMPT = """당신은 복지 정책 안내 서비스의 도구 선택(Tool Router) 에이전트입니다.
사용자 질문을 보고 아래 네 가지 도구 중 하나를 호출하세요.
질문이 정책 내용과 최신성을 동시에 묻고 있다면 policy_search_tool과
web_search_tool을 함께 호출해도 됩니다.
직접 답변을 작성하지 말고, 오직 tool_call만 생성하세요.
1. policy_search_tool - 정책 지원 대상, 신청 방법, 세부 조건 등 정책 자체 질문
2. web_search_tool - 최신성이 필요하거나 정보가 부족한 질문
3. general_response_tool - 복지 정책과 무관한 질문
4. welfare_recommendation_tool - 사용자 개인 정보 기반 맞춤 복지 추천 요청
   ("저한테 맞는 복지 추천해줘", "내가 받을 수 있는 지원이 뭐야" 등)

질문 원문(query)을 그대로 tool의 인자로 전달하세요."""


def _build_recommendation_query(question: str, background: dict) -> str:
    """배경정보를 자연어로 풀어서 검색 쿼리에 녹인다."""
    parts = [question]
    if background.get("age") is not None:
        parts.append(f"{background['age']}세")
    if background.get("family_size") is not None:
        parts.append(f"가구원 수 {background['family_size']}명")
    if background.get("income") is not None:
        parts.append(f"월 소득 {background['income']}원")
    if background.get("employment_stat"):
        parts.append(str(background["employment_stat"]))
    if background.get("disability"):
        parts.append("장애인")
    return " ".join(parts)

 """배경정보를 답변에 그대로 인용할 수 있는 자연어 문장으로 만든다.

    LLM(tool_call 생성 시 content가 비는 경우가 많음)에 맡기지 않고
    여기서 직접 문장을 만들어 state.context에 넣는다. generate.py가
    이 텍스트를 다른 근거 문서와 함께 보고 답변 앞부분에 자연스럽게
    녹여 쓴다.
    """

def _describe_background(background: dict) -> str:
   
    parts = []
    if background.get("age") is not None:
        parts.append(f"만 {background['age']}세")
    if background.get("family_size") is not None:
        parts.append(f"가구원 수 {background['family_size']}명")
    if background.get("income") is not None:
        parts.append(f"월 소득 {background['income']:,}원")
    if background.get("employment_stat"):
        parts.append(str(background["employment_stat"]))
    parts.append("장애 등록 있음" if background.get("disability") else "장애 등록 없음")

    profile_text = ", ".join(parts)
    return (
        f"[사용자 정보] 회원님의 등록된 정보는 {profile_text}입니다. "
        "이 정보를 기준으로 아래 정책을 추천합니다."
    )


async def information_agent(state: ChatState) -> dict:
    question = state["question"]

    history_messages = []
    for turn in state.get("chat_history") or []:
        role = turn.get("role")
        content = turn.get("content", "")
        if role == "user":
            history_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            history_messages.append(AIMessage(content=content))

    response = await _llm_with_tools.ainvoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            *history_messages,
            HumanMessage(content=question),
        ]
    )

    tool_calls = getattr(response, "tool_calls", None) or []

    print("------ INFORMATION AGENT ------")
    print(f"question: {question}")
    print(f"tool_calls: {tool_calls}")
    print(f"response.content (tool 미선택 시 여기에 텍스트가 들어옴): {response.content!r}")
    print("--------------------------------")
    wants_recommendation = any(
        tc["name"] == "welfare_recommendation_tool" for tc in tool_calls
    )

    if wants_recommendation:
        background = state.get("user_background")

        if not is_background_complete(background):
            return {"answer": PROFILE_REQUIRED_MESSAGE}

        enriched_query = _build_recommendation_query(question, background)
        background_summary = _describe_background(background)
        synthetic_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "policy_search_tool",
                    "args": {"query": enriched_query},
                    "id": f"call_{uuid.uuid4().hex}",
                }
            ],
        )
        return {
            "messages": [synthetic_response],
            "context": [background_summary],
        }

    return {"messages": [response]}