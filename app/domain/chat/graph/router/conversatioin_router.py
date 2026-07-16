from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
# from app.infrastructure.llm.ollama import get_llm
from app.infrastructure.llm.gpt import get_llm_gpt

llm = get_llm_gpt()
#--------------------------------
# 대화 상태 Router 추가
class ConversationRoute(BaseModel):
    mode: str = Field(
        description="general 또는 application"
    )
conversation_system = """
                     너는 현재 대화 상태를 판단하는 라우터다.

                     application:
                     - 사용자가 복지 신청을 진행 중인 경우
                     - 이전 대화에서 특정 정책 신청 흐름이 이어지는 경우
                     - 신청 자격, 서류, 신청서 작성, 진행 상황 관련 질문

                     general:
                     - 단순 정책 검색
                     - 복지 제도 정보 탐색
                     - 일반적인 복지 질문
                     - 일상 대화

                     판단할 때 현재 질문만 보지 말고 이전 대화 맥락을 반드시 고려한다.

                     반드시 general 또는 application 중 하나만 반환한다.
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
# 매 질문마다 현재 질문 + 이전 대화 + 현재 신청 상태 보고 결정 
    result = await conversation_router.ainvoke(
        {
            "question": state["question"],
            "chat_history": state.get("chat_history", [])
        }
    )
    print("CONVERSATION MODE:", result.mode)
    return result.mode