"""자연어 구독 요청을 안전한 도메인 서비스 호출로 변환하는 에이전트 노드."""

import logging
import re
import uuid
from datetime import timedelta
from typing import Literal

from fastapi.concurrency import run_in_threadpool
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.common.exceptions import SubscriptionError
from app.common.timezone import now_kst
from app.domain.chat.graph.state import ChatGraphState
from app.domain.subscription.entity.models import SubscriptionDialog
from app.domain.subscription.repository import (
    SubscriptionDialogRepository,
    SubscriptionRepository,
)
from app.domain.subscription.service.subscription_service import (
    PolicySubscriptionService,
)
from app.infrastructure.db.connection import engine
from app.infrastructure.llm.ollama import get_llm
from app.infrastructure.vectorstore.setup_vectorstore import get_ensemble_retriever

logger = logging.getLogger(__name__)


class SubscriptionIntent(BaseModel):
    """LLM이 반환할 수 있는 액션을 서버가 허용한 값으로 제한한다."""

    action: Literal[
        "subscribe",
        "unsubscribe",
        "list_subscriptions",
        "enable_policy_news",
        "disable_policy_news",
        "pause_all",
        "resume_all",
        "not_subscription",
    ] = Field(description="사용자가 요청한 구독 관련 동작")
    policy_query: str | None = Field(
        default=None,
        description="구독 또는 해지할 정책을 찾기 위한 검색어",
    )


_intent_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """너는 복지 정책 알림 구독 요청을 구조화하는 라우터다.
사용자의 문장을 허용된 action 중 하나로 분류하고, 특정 정책이 언급되면
불필요한 '알려줘', '구독해줘' 같은 표현을 제외한 policy_query를 반환한다.
정책 마감 알림 요청은 subscribe, 알림 해지는 unsubscribe로 분류한다.
설정과 무관한 요청은 not_subscription으로 분류한다.""",
        ),
        ("human", "{question}"),
    ]
)
_intent_chain = _intent_prompt | get_llm().with_structured_output(SubscriptionIntent)

_POSITIVE = {"네", "예", "응", "좋아", "확인", "등록", "해줘", "맞아", "yes", "y"}
_NEGATIVE = {"아니", "아니요", "취소", "그만", "됐어", "no", "n"}


def _normalized_answer(text: str) -> str:
    return re.sub(r"[\s.!?]+", "", text).lower()


def _is_positive(text: str) -> bool:
    answer = _normalized_answer(text)
    return answer in _POSITIVE or answer.startswith("네") or answer.startswith("예")


def _is_negative(text: str) -> bool:
    answer = _normalized_answer(text)
    return answer in _NEGATIVE or answer.startswith("아니") or "취소" in answer


def _format_policy(policy, index: int | None = None) -> str:
    prefix = f"{index}. " if index is not None else ""
    deadline = (
        policy.application_deadline.isoformat()
        if policy.application_deadline is not None
        else "마감일 미정"
    )
    return f"{prefix}{policy.service_name} ({policy.department}, 마감: {deadline})"


def _confirmation_message(action: str, policy) -> str:
    if action == "subscribe":
        return (
            f"‘{policy.service_name}’ 정책을 구독하시겠어요?\n"
            f"- 신청 마감일: {policy.application_deadline.isoformat()}\n"
            "- 알림 시점: 마감 7일 전, 1일 전\n"
            "- 알림 채널: 이메일\n\n"
            "등록하려면 ‘네’, 취소하려면 ‘아니요’라고 답해 주세요."
        )
    return (
        f"‘{policy.service_name}’ 정책의 마감 알림을 해지하시겠어요?\n"
        "해지하려면 ‘네’, 유지하려면 ‘아니요’라고 답해 주세요."
    )


def _search_candidates(
    session: Session,
    user_id: uuid.UUID,
    query: str,
    action: str,
) -> list:
    repo = SubscriptionRepository(session)
    candidates = repo.search_policies(query, limit=3)

    # 이름 검색만으로 충분하지 않을 때 기존 하이브리드 검색을 보조 수단으로 쓴다.
    # 벡터 메타데이터의 ID를 그대로 신뢰하지 않고 정형 정책 테이블에서 재조회한다.
    if len(candidates) < 3:
        try:
            documents = get_ensemble_retriever().invoke(query)
        except Exception:  # noqa: BLE001
            # 외부 임베딩/벡터 검색 장애가 구독 전체를 막지 않도록 이름 검색
            # 결과는 그대로 사용한다. 상세 원인은 서버 로그에서만 확인한다.
            logger.exception("구독 정책 벡터 검색 실패: query=%s", query)
            documents = []
        seen = {policy.service_id for policy in candidates}
        for document in documents:
            service_id = document.metadata.get("service_id")
            if not service_id or service_id in seen:
                continue
            policy = repo.get_policy_by_service_id(str(service_id))
            if policy is not None and policy.status == "active":
                candidates.append(policy)
                seen.add(policy.service_id)
            if len(candidates) == 3:
                break

    if action == "unsubscribe":
        subscribed_ids = {item.policy_id for item in repo.list_active(user_id)}
        candidates = [policy for policy in candidates if policy.id in subscribed_ids]
    return candidates[:3]


def _find_selection(question: str, policies: list) -> object | None:
    """번호를 우선 해석하고, 없으면 정책명이 포함됐는지 확인한다."""
    number = re.search(r"(?:^|\D)([1-3])(?:번|번째)?(?:\D|$)", question)
    if number:
        index = int(number.group(1)) - 1
        if 0 <= index < len(policies):
            return policies[index]
    normalized = _normalized_answer(question)
    for policy in policies:
        if _normalized_answer(policy.service_name) in normalized:
            return policy
    return None


def _create_dialog(
    session: Session,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    action: str,
    query: str,
    policies: list,
) -> tuple[SubscriptionDialog, str]:
    dialog_repo = SubscriptionDialogRepository(session)
    expires_at = now_kst() + timedelta(minutes=30)

    if len(policies) == 1:
        policy = policies[0]
        if action == "subscribe":
            PolicySubscriptionService(session).validate_subscribable(policy.id)
        dialog = SubscriptionDialog(
            conversation_id=conversation_id,
            user_id=user_id,
            action=action,
            stage="awaiting_confirmation",
            policy_query=query,
            candidate_policy_ids=[policy.id],
            selected_policy_id=policy.id,
            expires_at=expires_at,
        )
        dialog_repo.save(dialog)
        return dialog, _confirmation_message(action, policy)

    dialog = SubscriptionDialog(
        conversation_id=conversation_id,
        user_id=user_id,
        action=action,
        stage="awaiting_selection",
        policy_query=query,
        candidate_policy_ids=[policy.id for policy in policies],
        expires_at=expires_at,
    )
    dialog_repo.save(dialog)
    lines = ["다음 중 어떤 정책을 말씀하시는지 선택해 주세요."]
    lines.extend(_format_policy(policy, index) for index, policy in enumerate(policies, 1))
    lines.append("번호 또는 정책명으로 답해 주세요.")
    return dialog, "\n".join(lines)


def _handle_active_dialog(
    session: Session,
    dialog: SubscriptionDialog,
    question: str,
) -> str:
    dialog_repo = SubscriptionDialogRepository(session)
    repo = SubscriptionRepository(session)
    policies = repo.get_policies(dialog.candidate_policy_ids)

    if dialog.stage == "awaiting_selection":
        policy = _find_selection(question, policies)
        if policy is None:
            return "정책을 선택하지 못했습니다. 앞서 안내한 1~3번 또는 정책명으로 답해 주세요."
        try:
            if dialog.action == "subscribe":
                PolicySubscriptionService(session).validate_subscribable(policy.id)
        except SubscriptionError as exc:
            dialog_repo.finish(dialog, "cancelled")
            return exc.message
        dialog.selected_policy_id = policy.id
        dialog.stage = "awaiting_confirmation"
        dialog.expires_at = now_kst() + timedelta(minutes=30)
        dialog_repo.save(dialog)
        return _confirmation_message(dialog.action, policy)

    if dialog.stage == "awaiting_confirmation":
        policy = repo.get_policy(dialog.selected_policy_id)
        if policy is None:
            dialog_repo.finish(dialog, "cancelled")
            return "선택한 정책을 더 이상 찾을 수 없어 요청을 취소했습니다."
        if _is_negative(question):
            dialog_repo.finish(dialog, "cancelled")
            return "요청을 취소했습니다. 기존 알림 설정은 변경되지 않았습니다."
        if not _is_positive(question):
            return "변경 내용을 확정하려면 ‘네’, 취소하려면 ‘아니요’라고 답해 주세요."

        service = PolicySubscriptionService(session)
        try:
            if dialog.action == "subscribe":
                _, changed = service.subscribe(dialog.user_id, policy.id)
                message = (
                    f"‘{policy.service_name}’ 구독을 등록했습니다. "
                    "마감 7일 전과 1일 전에 이메일로 알려드릴 예정입니다."
                    if changed
                    else f"‘{policy.service_name}’ 정책은 이미 구독 중입니다."
                )
            else:
                service.unsubscribe(dialog.user_id, policy.id)
                message = f"‘{policy.service_name}’ 정책의 마감 알림을 해지했습니다."
        except SubscriptionError as exc:
            message = exc.message
            dialog_repo.finish(dialog, "cancelled")
            return message
        dialog_repo.finish(dialog)
        return message

    return "진행 중인 구독 요청이 만료되었습니다. 다시 요청해 주세요."


def _handle_new_intent(
    session: Session,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    intent: SubscriptionIntent,
) -> str:
    service = PolicySubscriptionService(session)
    action = intent.action

    if action == "list_subscriptions":
        rows = service.list_subscriptions(user_id)
        if not rows:
            return "현재 구독 중인 정책이 없습니다."
        lines = ["현재 구독 중인 정책입니다."]
        lines.extend(
            _format_policy(policy, index)
            for index, (_, policy) in enumerate(rows, 1)
        )
        return "\n".join(lines)
    if action == "enable_policy_news":
        service.set_policy_news(user_id, True)
        return "신규·폐지 정책 소식 이메일을 받도록 설정했습니다."
    if action == "disable_policy_news":
        service.set_policy_news(user_id, False)
        return "신규·폐지 정책 소식 이메일을 받지 않도록 설정했습니다."
    if action == "pause_all":
        service.set_paused(user_id, True)
        return "모든 정책 알림을 일시 중지했습니다."
    if action == "resume_all":
        service.set_paused(user_id, False)
        return "정책 알림을 다시 받도록 설정했습니다."
    if action not in {"subscribe", "unsubscribe"}:
        return "구독 요청을 이해하지 못했습니다. 구독할 정책명을 함께 알려주세요."
    if not intent.policy_query or not intent.policy_query.strip():
        verb = "구독" if action == "subscribe" else "해지"
        return f"어떤 정책을 {verb}할지 정책명을 알려주세요."

    candidates = _search_candidates(
        session, user_id, intent.policy_query.strip(), action
    )
    if not candidates:
        return (
            "구독 중인 정책에서 일치하는 항목을 찾지 못했습니다."
            if action == "unsubscribe"
            else "일치하는 정책을 찾지 못했습니다. 정책명을 조금 더 구체적으로 알려주세요."
        )
    try:
        _, message = _create_dialog(
            session,
            conversation_id,
            user_id,
            action,
            intent.policy_query.strip(),
            candidates,
        )
        return message
    except SubscriptionError as exc:
        return exc.message


async def subscription_agent(state: ChatGraphState) -> dict:
    """현재 대화 단계에 맞춰 구독 요청 한 턴을 처리한다."""
    user_id = uuid.UUID(str(state["user_id"]))
    conversation_id = uuid.UUID(str(state["conversation_id"]))
    question = state["question"]

    def load_dialog():
        with Session(engine) as session:
            return SubscriptionDialogRepository(session).get_active(
                conversation_id, user_id
            )

    active_dialog = await run_in_threadpool(load_dialog)
    if active_dialog is not None:
        def handle_active():
            with Session(engine) as session:
                # 다른 Session에서 사용할 수 있도록 같은 ID로 다시 읽는다.
                dialog = session.get(SubscriptionDialog, active_dialog.id)
                if dialog is None:
                    return "진행 중인 구독 요청을 찾을 수 없습니다. 다시 요청해 주세요."
                return _handle_active_dialog(session, dialog, question)

        generation = await run_in_threadpool(handle_active)
    else:
        intent = await _intent_chain.ainvoke({"question": question})

        def handle_new():
            with Session(engine) as session:
                return _handle_new_intent(
                    session, user_id, conversation_id, intent
                )

        generation = await run_in_threadpool(handle_new)

    return {
        "generation": generation,
        "conversation_mode": "subscription",
        "route": "subscription",
    }
