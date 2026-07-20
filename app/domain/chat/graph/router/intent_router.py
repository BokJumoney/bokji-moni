"""
Intent Router.

사용자 질문을 아래 3개 에이전트 중 하나로 분류한다. (chat_graph.py의
conditional edges 매핑과 정확히 같은 3개 키를 반환해야 함)

    1. information_agent  : 복지 정책 정보 제공 (지원 대상, 신청 방법, 정책 설명,
                             구비서류 등) + 복지와 무관한 질문도 일단 여기로 보내서
                             내부 general_response_tool이 안내하도록 함
    2. subscription_graph : 정책 구독/알림 관리 (아직 미구현 -> chat_graph.py에서
                             coming_soon으로 매핑됨)
    3. eligibility_agent  : 자격요건 판별 (아직 미구현 -> chat_graph.py에서
                             coming_soon으로 매핑됨)

※ 별도의 casual_talk 카테고리는 두지 않는다. "날씨 알려줘" 같은 복지 무관
  질문도 information_agent로 보내고, information_agent 내부의
  general_response_tool이 "저는 복지 정책 안내 서비스입니다" 라고 응답한다.
"""
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.domain.chat.graph.state2 import ChatState
from app.infrastructure.llm.gpt import get_llm_gpt

# 프롬프트
router_system = """
    당신은 사용자의 질문을 분석하여 적절한 처리 에이전트로 분류하는 라우터입니다.
    다음 세 가지 카테고리 중 하나로만 분류하세요:

    1. information_agent: 복지 정책 자체에 대한 정보 질문, 그리고 그 외 모든 질문
       - 지원 대상, 신청 방법, 정책 설명, 구비서류, 세부 조건, 최신 정책 변경 여부 등
       - '복지'/'정책'이라는 단어가 없어도 '실직', '생활비 부족', '파산' 처럼
         정부 지원이 필요한 상황을 토로하는 경우도 포함
       - 복지 정책과 전혀 무관한 질문(날씨, 잡담, 코딩 등)도 이 카테고리로
         분류하세요. information_agent 내부에서 관련 없는 질문임을 판단해
         적절히 안내합니다.

    2. subscription_graph: 정책 알림/구독 관리 요청
       - 특정 정책이 새로 생기거나 바뀌면 알려달라는 요청
       - 이미 신청해둔 알림(구독) 목록 조회, 구독 해지/변경 요청

    3. eligibility_agent: 특정 정책에 대한 "내 자격 여부" 판별 요청
       - "내가 이거 받을 수 있어?", "나 자격 되는지 확인해줘" 처럼
         사용자 본인의 조건(나이/소득/거주지 등)을 정책 기준과 대조해서
         해당 여부를 판단해달라는 질문
       - 단순히 "지원 대상이 뭐야?"라고 정책 기준 자체를 묻는 것은
         information_agent이고, "그래서 나는 되는거야?"처럼 본인 상황과
         대조해달라는 것만 eligibility_agent 입니다.

    [카테고리 구분이 헷갈릴 때 우선순위]
    - "나"/"제 상황"처럼 본인 조건과 대조해달라는 요청이 명확하면 → eligibility_agent
    - "알림"/"구독"/"새로 생기면 알려줘"가 명확하면 → subscription_graph
    - 그 외에는(복지 관련이든 무관하든) 전부 → information_agent

    [예시]
    - "청년내일저축계좌 지원 대상 알려줘" -> information_agent
    - "실업급여 신청 어떻게 해?" -> information_agent
    - "제출 서류가 뭐예요?" -> information_agent
    - "재취업이 안 돼서 파산 직전이야, 도움 받을 데 있을까?" -> information_agent
    - "오늘 날씨 알려줘" -> information_agent
    - "돈 많이 버는 법 알려줘" -> information_agent
    - "청년 정책 새로 생기면 알림 보내줘" -> subscription_graph
    - "내가 구독한 정책 목록 보여줘" -> subscription_graph
    - "청년내일저축계좌 알림 해지해줘" -> subscription_graph
    - "나 청년내일저축계좌 받을 수 있어? 월급 250만원인데" -> eligibility_agent
    - "제가 이 조건에 해당되는지 확인해주세요" -> eligibility_agent

    [사용자 질문]
    "{question}"

    [출력 형식]
    아래 세 가지 중 하나의 텍스트만 반환하세요:
    information_agent 또는 subscription_graph 또는 eligibility_agent
"""


class RouteQuery(BaseModel):
    datasource: str = Field(
        description="information_agent 또는 subscription_graph 또는 eligibility_agent"
    )


route_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", router_system),
        ("human", "{question}"),
    ]
)

llm = get_llm_gpt()
question_router_llm = llm.with_structured_output(RouteQuery)
question_router = route_prompt | question_router_llm


def route_by_intent(state: ChatState) -> str:
    """intent_router 노드가 미리 저장해둔 state["intent"]를 그대로 반환한다.
    (LLM을 여기서 또 호출하지 않음 - 이미 intent_router 노드에서 판단 끝남)
    """
    return state["intent"]