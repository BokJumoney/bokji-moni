from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from app.domain.chat.graph.state import ChatGraphState
from app.infrastructure.config import settings
from app.infrastructure.llm.ollama import get_llm

# 일반 모드에서 사용자 질문 의도를 판단하는 Router
OLLAMA_MODEL = settings.LOCAL_MODEL
OLLAMA_BASE_URL = settings.LOCLAL_LLM_URL

# 프롬프트
router_system = """
    당신은 사용자의 질문을 분석하여 적절한 처리 노드로 분류하는 라우터입니다.
    다음 세 가지 카테고리 중 하나로만 분류하세요:
    1. vectorstore: 정부 지원, 복지 정책, 실업, 생활고, 금융 취약계층 지원 등 공공/민간 복지 서비스와 관련된 질문인 경우
    2. casual_talk: 일상적인 대화, 단순 인사, 복지 외 타 분야 질문인 경우
    3. application: 
    [주의 사항]
    - 사용자가 '복지'나 '정책'이라는 단어를 직접 사용하지 않더라도, '실직', '퇴사', '생활비 부족', '파산', '취업 실패' 등 정부의 도움이나 지원 제도가 필요한 상황을 토로하는 경우반드시 WELFARE_POLICY로 분류해야 합니다.

    [예시]
    - "28세 남성인데 직장 짤렸는데 재취업이 너무 안돼서 파산 직전이야... 도움 받을 수 있는거 있을까?" -> vectorstore
    - "실업급여 신청 어떻게 해?" -> vectorstore
    - "요즘 날씨가 너무 좋네. 오늘 뭐하지?" -> casual_talk
    - "돈 많이 버는 법 알려줘" -> casual_talk
    - "청년내일저축계좌 신청하고 싶어요." → application
    - "제출 서류가 뭐예요?" → application

    [사용자 질문]
    "{question}"

    [출력 형식]
    텍스트 형태로 반환하세요: vectorstore 또는 casual_talk 또는 application
"""

# Pydatic 객체로 받음
class RouteQuery(BaseModel):
    datasource: str = Field(description="vectorstore 또는 casual_talk 또는 application")

route_prompt = ChatPromptTemplate.from_messages([
    ("system", router_system),
    ("human", "{question}"),
])

llm = get_llm()

question_router_llm = llm.with_structured_output(RouteQuery)

question_router = route_prompt | question_router_llm

# 라우트 실행 함수 
async def route_question(state: ChatGraphState) -> str:
    """
    사용자 질문을 vectorstore 또는 casual_talk으로 라우팅한다.

    :param
        state (dict): 현재 graph state
    :return:
        str: 라우팅된 데이터 소스 (vectorstore 또는 casual_talk)
    """
    question = state["question"]
    route = await question_router.ainvoke({"question": question})
    return route.datasource


