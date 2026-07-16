from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
# from app.infrastructure.llm.ollama import get_llm
from app.infrastructure.llm.gpt import get_llm_gpt

llm = get_llm_gpt()
#--------------------------------
# 대화 상태 Router 추가
class ConversationRoute(BaseModel):
    mode: str = Field(
        description="general, application 또는 subscription"
    )
conversation_system = """
너는 현재 대화 상태를 판단하는 라우터다.

application:
- 신청하고 싶다
- 특정 복지 신청 진행 중
- 자격 확인 진행
- 제출 서류 확인 진행

subscription:
- 정책 알림 구독 후보 선택 진행
- 정책 구독 또는 해지 최종 확인 진행

general:
- 단순 정책 검색
- 복지 제도 정보 탐색
- 일반적인 복지 질문
- 일상 대화

판단할 때 현재 질문만 보지 말고 이전 대화 맥락을 반드시 고려한다.

반드시 general, application, subscription 중 하나만 반환한다.
"""

conversation_prompt = ChatPromptTemplate.from_messages([
    ("system", conversation_system),
    ("human", 
     """
     현재 질문:
     {question}

     이전 대화:
     {chat_history}
     """)
])


conversation_llm_router = llm.with_structured_output(ConversationRoute)


conversation_router = (
    conversation_prompt | conversation_llm_router
)


async def check_conversation_mode(state):

    # "1번", "네" 같은 후속 답변은 일반 의도 분류만으로 의미를 알 수 없다.
    # ChatService가 DB에서 복원한 진행 모드를 가장 먼저 존중한다.
    if state.get("conversation_mode") == "subscription":
        return "subscription"

    if state.get("conversation_mode") == "application":
        return "application"

    # result = await conversation_router.ainvoke(
    #     {
    #         "question": state["question"],
    #         "chat_history": state["chat_history"]
    #     }
    # )

    return "general"
