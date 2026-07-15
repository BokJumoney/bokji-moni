from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from app.infrastructure.llm.ollama import get_llm

llm = get_llm()
#--------------------------------
# 대화 상태 Router 추가
class ConversationRoute(BaseModel):
    mode: str = Field(
        description="general 또는 application"
    )
conversation_system = """
                     너는 현재 대화 상태를 판단하는 라우터다.

                     application:
                     - 신청하고 싶다
                     - 특정 복지 신청 진행 중
                     - 자격 확인 진행
                     - 제출 서류 확인 진행

                     general:
                     - 정책 검색
                     - 일반 복지 질문
                     - 일상 대화

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

    if state.get("conversation_mode") == "application":
        return "application"

    # result = await conversation_router.ainvoke(
    #     {
    #         "question": state["question"],
    #         "chat_history": state["chat_history"]
    #     }
    # )

    return "general"