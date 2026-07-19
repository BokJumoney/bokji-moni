"""
Agent (Tool 선택).

Intent Router가 "정보 조회 / 자격 요건 판단" 계열 질문으로 분류한 뒤
호출되는 노드. 3개의 Tool 중 하나를 골라 tool_call을 만든다.
필요하면 여러 도구를 동시에 호출해도 된다

  1. policy_search_tool     - 복지 정책 자체에 대한 질문
  2. web_search_tool        - 최신성이 필요하거나 정보가 부족한 질문
  3. general_response_tool  - 복지 정책과 무관한 질문

실제 Tool 실행은 이 노드가 하지 않는다. 이 노드는 "어떤 Tool을,
어떤 인자로 호출할지"만 결정한 AIMessage(tool_calls 포함)를
state.messages에 추가하고, 실행은 router/tool_router.py →
nodes/tool_executor.py 로 이어진다.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.infrastructure.config import settings
from app.domain.chat.graph.state2 import ChatState
from app.domain.chat.graph.tools.policy_search import policy_search_tool
from app.domain.chat.graph.tools.web_search import web_search_tool
from app.domain.chat.graph.tools.general_response import general_response_tool

TOOLS = [policy_search_tool, web_search_tool, general_response_tool]

_llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=settings.openai_api_key,
    temperature=0,
)

_llm_with_tools = _llm.bind_tools(TOOLS)

SYSTEM_PROMPT = """당신은 복지 정책 안내 서비스의 도구 선택(Tool Router) 에이전트입니다.
사용자 질문을 보고 아래 세 가지 도구 중 하나를 호출하세요.
질문이 정책 내용과 최신성(변경 여부, 신규 정책 등)을 동시에 묻고 있다면
policy_search_tool과 web_search_tool을 함께(동시에) 호출해도 됩니다.
직접 답변을 작성하지 말고, 오직 tool_call만 생성하세요.

1. policy_search_tool
   복지 정책의 지원 대상, 신청 방법, 정책 설명, 구비서류, 서식,
   세부 조건 등 정책 자체에 대한 질문일 때 사용합니다.

2. web_search_tool
   "올해/2026년 새로 생긴 정책", "신청 기간이 바뀌었는지",
   "최근 정책이 변경되었는지" 등 최신성이 필요한 질문이거나,
   policy_search_tool로 답하기에 정보가 부족하다고 판단될 때 사용합니다.

3. general_response_tool
   복지 정책과 무관한 질문(날씨, 일반 상식, 코딩 등)일 때 사용합니다.

질문 원문(query)을 그대로 tool의 인자로 전달하세요."""


async def information_agent(state: ChatState) -> dict:
    question = state["question"]

    response = await _llm_with_tools.ainvoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=question),
        ]
    )

    return {"messages": [response]}
