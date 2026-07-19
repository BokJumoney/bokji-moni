"""인증 사용자 컨텍스트가 주입된 구독 Tool factory.

모델이 선택할 수 있는 인자는 정책 검색어와 설정값뿐이다. 데이터 소유권의
기준인 ``user_id``는 서버가 만든 실행 컨텍스트에서 각 Tool의 클로저로
주입하므로, 모델이 다른 사용자의 ID를 만들거나 바꿀 수 없다.
"""

from collections.abc import Callable
from typing import TypeVar

from langchain_core.tools import BaseTool, StructuredTool
from sqlmodel import Session

from app.domain.subscription.agent.schemas import (
    BooleanSettingInput,
    EmptyToolInput,
    PolicyQueryInput,
    SubscriptionExecutionContext,
)
from app.domain.subscription.service.subscription_service import (
    SubscriptionApplicationService,
)
from app.infrastructure.db.connection import engine

T = TypeVar("T")


def _with_service(
    operation: Callable[[SubscriptionApplicationService], T],
) -> T:
    """각 DB 작업마다 새 세션을 열어 Tool 간 트랜잭션 공유를 막는다."""
    with Session(engine) as session:
        return operation(SubscriptionApplicationService(session))


def _candidate_message(
    heading: str,
    candidates: list[tuple[str, str]],
) -> str:
    """후보가 모호할 때 모델의 추측 대신 사용자가 재선택할 목록을 만든다."""
    lines = [heading]
    lines.extend(f"- {name} ({service_id})" for service_id, name in candidates)
    lines.append(
        "정확한 정책명이나 괄호 안 정책 ID와 함께 구독 또는 해지를 다시 요청해 주세요."
    )
    return "\n".join(lines)


def _select_policy_candidate(
    query: str,
    candidates: list[tuple[str, str]],
) -> tuple[str, str] | None:
    """정확히 일치하거나 후보가 하나일 때만 변경 대상을 확정한다."""
    normalized = query.strip().casefold()
    exact = [
        candidate
        for candidate in candidates
        if normalized
        in (
            candidate[0].strip().casefold(),
            candidate[1].strip().casefold(),
        )
    ]
    if len(exact) == 1:
        return exact[0]
    if len(candidates) == 1:
        return candidates[0]
    return None


def build_subscription_tools(
    context: SubscriptionExecutionContext,
) -> list[BaseTool]:
    """인증된 ``user_id``를 클로저에 고정한 요청 전용 Tool 목록을 만든다.

    각 ``args_schema``에는 ``user_id``가 없으므로 LLM은 인증 범위를
    우회할 수 없고, 모든 개인 데이터 작업은 이 함수가 받은 사용자에게만
    적용된다.
    """

    def list_my_subscriptions() -> str:
        """현재 사용자의 구독 스냅샷을 사람이 읽을 수 있는 목록으로 반환한다."""
        result = _with_service(
            lambda service: service.list_subscriptions(context.user_id)
        )
        if not result.items:
            return "현재 구독 중인 정책이 없습니다."

        lines = ["현재 구독 중인 정책입니다."]
        for item in result.items:
            deadline = (
                item.application_deadline.isoformat()
                if item.application_deadline
                else "날짜 정보 없음"
            )
            lines.append(
                f"- {item.service_name} ({item.service_id}), 신청 마감: {deadline}"
            )
        return "\n".join(lines)

    def get_my_notification_preferences() -> str:
        """두 알림 설정을 DB에서 읽어 현재 상태를 명시적으로 반환한다."""
        settings = _with_service(
            lambda service: service.get_settings(context.user_id)
        )
        policy_news = "켜짐" if settings.policy_news_enabled else "꺼짐"
        pause = "켜짐" if settings.is_paused else "꺼짐"
        return (
            f"전체 정책 소식 수신: {policy_news}\n"
            f"모든 알림 일시 중지: {pause}"
        )

    def subscribe_policy(query: str) -> str:
        """정책 후보를 안전하게 확정한 뒤 현재 사용자에게 구독을 추가한다."""
        candidates = _with_service(
            lambda service: service.find_policy_candidates(query)
        )
        if not candidates:
            return "구독할 정책을 찾지 못했습니다. 정책명이나 정책 ID를 확인해 주세요."

        selected = _select_policy_candidate(query, candidates)
        if selected is None:
            return _candidate_message(
                "여러 정책이 검색되었습니다.",
                candidates,
            )

        service_id, service_name = selected
        item = _with_service(
            lambda service: service.subscribe(
                context.user_id,
                service_id,
                service_name,
            )
        )
        return f"{item.service_name} ({item.service_id}) 정책 알림을 구독했습니다."

    def unsubscribe_policy(query: str) -> str:
        """현재 사용자의 구독 안에서만 해지 후보를 찾고 삭제한다."""
        rows = _with_service(
            lambda service: service.find_subscription_candidates(
                context.user_id,
                query,
            )
        )
        candidates = [(row.service_id, row.service_name) for row in rows]
        if not candidates:
            return "해지할 구독을 찾지 못했습니다."

        selected = _select_policy_candidate(query, candidates)
        if selected is None:
            return _candidate_message(
                "여러 구독 정책이 검색되었습니다.",
                candidates,
            )

        service_id, service_name = selected
        deleted = _with_service(
            lambda service: service.unsubscribe(context.user_id, service_id)
        )
        if not deleted:
            return "이미 해지되었거나 구독 중이 아닌 정책입니다."
        return f"{service_name} ({service_id}) 정책 알림을 해지했습니다."

    def set_policy_news(enabled: bool) -> str:
        """정책 소식 수신 설정만 변경하고 저장된 결과를 반환한다."""
        settings = _with_service(
            lambda service: service.update_policy_news(context.user_id, enabled)
        )
        value = "받도록" if settings.policy_news_enabled else "받지 않도록"
        return f"전체 정책 소식을 {value} 설정했습니다."

    def set_notification_pause(enabled: bool) -> str:
        """전체 알림 일시 중지 설정만 변경하고 저장된 결과를 반환한다."""
        settings = _with_service(
            lambda service: service.update_pause(context.user_id, enabled)
        )
        value = (
            "일시 중지했습니다"
            if settings.is_paused
            else "다시 받도록 설정했습니다"
        )
        return f"모든 알림을 {value}."

    # 이름과 설명은 모델의 Tool 선택용이고, args_schema는 실행 시 입력 검증용이다.
    return [
        StructuredTool.from_function(
            func=list_my_subscriptions,
            name="list_my_subscriptions",
            description="현재 로그인 사용자가 구독한 정책 목록을 조회한다.",
            args_schema=EmptyToolInput,
        ),
        StructuredTool.from_function(
            func=get_my_notification_preferences,
            name="get_my_notification_preferences",
            description="현재 로그인 사용자의 정책 소식과 일시 중지 설정을 조회한다.",
            args_schema=EmptyToolInput,
        ),
        StructuredTool.from_function(
            func=subscribe_policy,
            name="subscribe_policy",
            description="정책 ID 또는 정책명으로 마감 알림 구독을 추가한다.",
            args_schema=PolicyQueryInput,
        ),
        StructuredTool.from_function(
            func=unsubscribe_policy,
            name="unsubscribe_policy",
            description="정책 ID 또는 정책명으로 기존 마감 알림 구독을 해지한다.",
            args_schema=PolicyQueryInput,
        ),
        StructuredTool.from_function(
            func=set_policy_news,
            name="set_policy_news",
            description="전체 정책 소식 수신 여부를 변경한다.",
            args_schema=BooleanSettingInput,
        ),
        StructuredTool.from_function(
            func=set_notification_pause,
            name="set_notification_pause",
            description="모든 알림의 일시 중지 여부를 변경한다.",
            args_schema=BooleanSettingInput,
        ),
    ]
