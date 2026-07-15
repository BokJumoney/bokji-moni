from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from app.domain.chat.graph.state import ChatGraphState
from app.infrastructure.llm.ollama import get_llm


llm = get_llm()


class ApplicationRoute(BaseModel):
    step: str = Field(
        description="""
        아래 중 하나만 반환:
        qualification
        document
        form
        vectorstore
        """
    )


application_system = """
너는 복지 신청 보조 라우터다.

사용자의 질문을 보고 적절한 노드로 이동시켜라.

qualification:
- 신청 자격
- 대상 여부
- 나이 조건
- 소득 기준
- 선정 기준

document:
- 제출 서류
- 준비해야 하는 자료
- 필요한 증빙서류

form:
- 신청서 작성 방법
- 신청서 항목 설명
- 체크박스 작성 방법
- 서식 관련 질문

vectorstore:
- 정책 내용
- 지원 내용
- 지원 금액
- 복지 제도 설명

반드시 qualification, document, form, vectorstore 중 하나만 반환한다.
"""


application_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", application_system),
        (
            "human",
            """
현재 진행 단계:
{current_step}

사용자 질문:
{question}
"""
        ),
    ]
)


application_router_chain = (
    application_prompt
    | llm.with_structured_output(ApplicationRoute)
)


async def application_router(state: ChatGraphState):

    result = await application_router_chain.ainvoke(
        {
            "question": state["question"],
            "current_step": state.get("current_step")
        }
    )

    return result.step