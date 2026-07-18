"""사용자 질문을 실제 처리 노드로 분류하는 Intent Router."""

from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.domain.chat.graph.state2 import ChatState
from app.infrastructure.llm.gpt import get_llm_gpt


router_system = """
당신은 사용자의 질문을 아래 네 가지 카테고리 중 하나로 분류합니다.

1. information_agent
   정책 설명, 지원 대상, 신청 방법, 구비서류 목록 등 정보 질문입니다.
   복지와 무관한 질문도 이 카테고리로 분류합니다.

2. subscription_agent
   정책 알림 구독, 구독 목록 조회, 구독 해지 요청입니다.

3. file_credential_agent
   실제 정책 신청서 또는 서식 파일을 내려받으려는 요청입니다.
   "구비서류가 뭐야?" 같은 목록 질문은 information_agent이며,
   "신청서 파일 줘", "서식 다운로드할래" 같은 요청만 여기에 해당합니다.

    [예시]
    - "청년내일저축계좌 지원 대상 알려줘" -> information_agent
    - "실업급여 신청 어떻게 해?" -> information_agent
    - "제출 서류가 뭐예요?" -> information_agent
    - "재취업이 안 돼서 파산 직전이야, 도움 받을 데 있을까?" -> information_agent
    - "오늘 날씨 알려줘" -> information_agent
    - "돈 많이 버는 법 알려줘" -> information_agent
    - "청년 정책 새로 생기면 알림 보내줘" -> subscription_agent
    - "내가 구독한 정책 목록 보여줘" -> subscription_agent
    - "청년내일저축계좌 알림 해지해줘" -> subscription_agent
    - "나 청년내일저축계좌 받을 수 있어? 월급 250만원인데" -> file_credential_agent
    - "제가 이 조건에 해당되는지 확인해주세요" -> file_credential_agent

    [사용자 질문]
    "{question}"

    [출력 형식]
    아래 세 가지 중 하나의 텍스트만 반환하세요:
    information_agent 또는 subscription_agent 또는 file_credential_agent
"""


class RouteQuery(BaseModel):
    datasource: Literal[
        "information_agent",
        "subscription_agent",
        "file_credential_agent",
    ] = Field(
        description=(
            "information_agent, subscription_agent 또는 "
            "file_credential_agent"
        )
    )


route_prompt = ChatPromptTemplate.from_messages(
    [("system", router_system), ("human", "{question}")]
)
question_router = route_prompt | get_llm_gpt().with_structured_output(RouteQuery)


def route_by_intent(state: ChatState) -> str:
    """intent_router 노드가 미리 저장해둔 state["intent"]를 그대로 반환한다.
    (LLM을 여기서 또 호출하지 않음 - 이미 intent_router 노드에서 판단 끝남)
    """
    return state["intent"]