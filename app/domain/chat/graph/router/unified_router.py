"""메인 채팅 그래프의 최종 진입 경로를 한 번에 결정하는 통합 라우터.

진행 중인 업무 대화는 "네", "2번"처럼 문장 자체만으로 분류하기 어려운
답변을 포함한다. 따라서 저장된 대화 모드를 먼저 확인하고, 진행 중인 업무가
없을 때만 LLM으로 새로운 질문의 의도를 분류한다.
"""

import logging
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.domain.chat.graph.state import ChatGraphState
from app.infrastructure.llm.ollama import get_llm

logger = logging.getLogger(__name__)

RouteName = Literal["vectorstore", "casual_talk", "application", "subscription"]


class UnifiedRoute(BaseModel):
    """LLM이 메인 그래프에 존재하지 않는 경로를 반환하지 못하게 제한한다."""

    route: RouteName = Field(description="사용자 요청을 처리할 최종 그래프 경로")


_router_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """너는 복지 서비스 채팅의 통합 라우터다.
현재 질문과 이전 대화를 보고 다음 경로 중 정확히 하나를 선택한다.

vectorstore:
- 복지 정책 검색, 추천, 대상 및 자격에 대한 일반 질문
- 실직, 생활고처럼 지원 제도를 찾아야 하는 상황

casual_talk:
- 단순 인사, 일상 대화, 복지와 무관한 질문

application:
- 특정 복지 정책을 신청하려는 요청
- 신청 자격, 제출 서류, 신청 절차를 진행하려는 요청

subscription:
- 특정 정책의 마감 알림 구독 또는 해지
- 구독 목록 조회
- 신규·폐지 정책 소식 설정
- 모든 정책 알림 일시 중지 또는 재개

주의:
- '청년내일저축계좌 신청하고 싶어'는 application이다.
- '청년내일저축계좌 마감 전에 알려줘'는 subscription이다.
- 단순히 정책을 알려달라는 요청은 vectorstore이다.""",
        ),
        (
            "human",
            """현재 질문:
{question}

이전 대화:
{chat_history}""",
        ),
    ]
)

_route_chain = _router_prompt | get_llm().with_structured_output(UnifiedRoute)


def _active_workflow_route(state: ChatGraphState) -> RouteName | None:
    """서버가 복원한 진행 상태를 신규 의도 분류보다 우선한다."""
    mode = state.get("conversation_mode")
    if mode == "subscription":
        return "subscription"
    if mode == "application":
        return "application"
    return None


async def unified_router(state: ChatGraphState) -> dict:
    """상태 우선 규칙과 신규 의도 분류를 합쳐 최종 경로를 반환한다."""
    conversation_id = state.get("conversation_id", "unknown")
    active_route = _active_workflow_route(state)
    if active_route is not None:
        logger.info(
            "대화 경로 결정: conversation_id=%s route=%s source=active_workflow",
            conversation_id,
            active_route,
        )
        return {"route": active_route, "route_source": "active_workflow"}

    try:
        result = await _route_chain.ainvoke(
            {
                "question": state.get("question", ""),
                "chat_history": state.get("chat_history", []),
            }
        )
        route: RouteName = result.route
    except Exception:  # noqa: BLE001
        # 라우터 장애 시 신청/구독처럼 DB를 변경할 수 있는 경로로 임의 진입하지
        # 않는다. 일반 응답 경로에서 안전하게 안내하도록 casual_talk을 택한다.
        logger.exception(
            "통합 라우터 호출 실패: conversation_id=%s", conversation_id
        )
        route = "casual_talk"

    logger.info(
        "대화 경로 결정: conversation_id=%s route=%s source=llm",
        conversation_id,
        route,
    )
    return {"route": route, "route_source": "llm"}
