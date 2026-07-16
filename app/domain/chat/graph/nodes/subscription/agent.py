"""자연어 구독 요청을 안전한 도메인 서비스 호출로 변환하는 에이전트 노드."""

import logging
import re
import uuid
from datetime import timedelta
from typing import Annotated, Literal

from fastapi.concurrency import run_in_threadpool
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
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

_tool_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """너는 복지 정책 알림 구독 도구를 선택하는 에이전트다.
사용자 요청 한 건에 도구를 정확히 하나만 호출한다.

- 현재 구독 목록 조회: list_policy_subscriptions
- 특정 정책 구독/해지: search_subscription_policies
- 신규·폐지 정책 소식 설정, 전체 알림 일시 중지/재개:
  request_notification_setting_change

정책 검색어에서 '알려줘', '구독해줘', '해지해줘' 같은 불필요한 표현은 제거한다.
사용자 ID나 대화방 ID를 추측하거나 도구 인자로 만들지 마라.""",
        ),
        ("human", "{question}"),
    ]
)

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


@tool(response_format="content_and_artifact")
def list_policy_subscriptions(
    user_id: Annotated[str, InjectedState("user_id")],
) -> tuple[str, dict]:
    """현재 사용자가 구독 중인 복지 정책 목록을 조회한다."""
    with Session(engine) as session:
        rows = PolicySubscriptionService(session).list_subscriptions(uuid.UUID(user_id))
        if not rows:
            message = "현재 구독 중인 정책이 없습니다."
            policy_ids: list[int] = []
        else:
            lines = ["현재 구독 중인 정책입니다."]
            lines.extend(
                _format_policy(policy, index)
                for index, (_, policy) in enumerate(rows, 1)
            )
            message = "\n".join(lines)
            policy_ids = [policy.id for _, policy in rows]
    return message, {"kind": "subscription_list", "policy_ids": policy_ids}


@tool(response_format="content_and_artifact")
def search_subscription_policies(
    policy_query: str,
    action: Literal["subscribe", "unsubscribe"],
    user_id: Annotated[str, InjectedState("user_id")],
) -> tuple[str, dict]:
    """구독하거나 해지할 정책 후보를 최대 3건 검색한다."""
    normalized_query = policy_query.strip()
    if not normalized_query:
        verb = "구독" if action == "subscribe" else "해지"
        message = f"어떤 정책을 {verb}할지 정책명을 알려주세요."
        return message, {
            "kind": "policy_candidates",
            "action": action,
            "policy_query": "",
            "candidate_policy_ids": [],
        }

    with Session(engine) as session:
        candidates = _search_candidates(
            session, uuid.UUID(user_id), normalized_query, action
        )
    if not candidates:
        message = (
            "구독 중인 정책에서 일치하는 항목을 찾지 못했습니다."
            if action == "unsubscribe"
            else "일치하는 정책을 찾지 못했습니다. 정책명을 조금 더 구체적으로 알려주세요."
        )
    else:
        message = f"{len(candidates)}건의 정책 후보를 찾았습니다."
    return message, {
        "kind": "policy_candidates",
        "action": action,
        "policy_query": normalized_query,
        "candidate_policy_ids": [policy.id for policy in candidates],
    }


@tool(response_format="content_and_artifact")
def request_notification_setting_change(
    action: Literal[
        "enable_policy_news",
        "disable_policy_news",
        "pause_all",
        "resume_all",
    ],
) -> tuple[str, dict]:
    """정책 소식 수신 또는 전체 알림 상태 변경 요청을 구조화한다.

    이 도구는 DB를 변경하지 않으며, 서버의 결정적 후처리가 실제 변경을 수행한다.
    """
    return "알림 설정 변경 요청을 확인했습니다.", {
        "kind": "notification_setting_change",
        "action": action,
    }


SUBSCRIPTION_TOOLS = [
    list_policy_subscriptions,
    search_subscription_policies,
    request_notification_setting_change,
]

_tool_chain = _tool_prompt | get_llm().bind_tools(
    SUBSCRIPTION_TOOLS,
    tool_choice="any",
)


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


def _subscription_result(generation: str) -> dict:
    """구독 경로의 공통 그래프 상태를 반환한다."""
    return {
        "generation": generation,
        "conversation_mode": "subscription",
        "route": "subscription",
    }


async def subscription_entry(state: ChatGraphState) -> dict:
    """활성 대화가 있으면 LLM 도구 선택을 건너뛴다."""
    user_id = uuid.UUID(str(state["user_id"]))
    conversation_id = uuid.UUID(str(state["conversation_id"]))

    def load_dialog():
        with Session(engine) as session:
            return SubscriptionDialogRepository(session).get_active(
                conversation_id, user_id
            )

    active_dialog = await run_in_threadpool(load_dialog)
    return {
        "subscription_stage": "active" if active_dialog is not None else "new"
    }


async def handle_active_subscription(state: ChatGraphState) -> dict:
    """저장된 후보 선택·확인 대화를 결정적으로 처리한다."""
    user_id = uuid.UUID(str(state["user_id"]))
    conversation_id = uuid.UUID(str(state["conversation_id"]))
    question = state["question"]

    def handle_active():
        with Session(engine) as session:
            dialog = SubscriptionDialogRepository(session).get_active(
                conversation_id, user_id
            )
            if dialog is None:
                return "진행 중인 구독 요청을 찾을 수 없습니다. 다시 요청해 주세요."
            return _handle_active_dialog(session, dialog, question)

    generation = await run_in_threadpool(handle_active)
    return _subscription_result(generation)


async def subscription_tool_agent(state: ChatGraphState) -> dict:
    """신규 구독 요청을 한 개의 허용된 도구 호출로 변환한다."""
    response = await _tool_chain.ainvoke({"question": state["question"]})
    return {"messages": [response]}


def route_tool_call(state: ChatGraphState) -> Literal["tools", "fallback"]:
    """LLM이 도구를 호출하지 않은 비정상 경우를 안전하게 종료한다."""
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        return "tools"
    return "fallback"


async def subscription_tool_fallback(_: ChatGraphState) -> dict:
    return _subscription_result(
        "구독 요청을 이해하지 못했습니다. "
        "구독할 정책명 또는 변경할 알림 설정을 알려주세요."
    )


def _apply_notification_setting(
    session: Session, user_id: uuid.UUID, action: str
) -> str:
    service = PolicySubscriptionService(session)
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
    return "알림 설정 변경 요청을 처리하지 못했습니다."


async def finalize_subscription_tool(state: ChatGraphState) -> dict:
    """도구 결과를 검증하고 대화 생성 또는 DB 변경을 수행한다."""
    tool_messages = [
        message
        for message in state.get("messages", [])
        if isinstance(message, ToolMessage)
    ]
    if len(tool_messages) != 1:
        return _subscription_result(
            "한 번에 하나의 구독 요청만 처리할 수 있습니다. "
            "원하는 작업을 하나만 다시 알려주세요."
        )

    tool_message = tool_messages[0]
    artifact = tool_message.artifact if isinstance(tool_message.artifact, dict) else {}
    kind = artifact.get("kind")
    if kind == "subscription_list":
        return _subscription_result(str(tool_message.content))

    user_id = uuid.UUID(str(state["user_id"]))
    conversation_id = uuid.UUID(str(state["conversation_id"]))

    if kind == "policy_candidates":
        candidate_ids = artifact.get("candidate_policy_ids", [])
        if not candidate_ids:
            return _subscription_result(str(tool_message.content))

        def create_dialog():
            with Session(engine) as session:
                policies = SubscriptionRepository(session).get_policies(candidate_ids)
                if not policies:
                    return "일치하는 정책을 더 이상 찾을 수 없습니다. 다시 검색해 주세요."
                try:
                    _, message = _create_dialog(
                        session,
                        conversation_id,
                        user_id,
                        str(artifact["action"]),
                        str(artifact["policy_query"]),
                        policies,
                    )
                    return message
                except SubscriptionError as exc:
                    return exc.message

        return _subscription_result(await run_in_threadpool(create_dialog))

    if kind == "notification_setting_change":
        def change_setting():
            with Session(engine) as session:
                return _apply_notification_setting(
                    session, user_id, str(artifact.get("action", ""))
                )

        return _subscription_result(await run_in_threadpool(change_setting))

        generation = await run_in_threadpool(handle_active)
    else:
        intent = await _intent_chain.ainvoke({"question": question})

        def handle_new():
            with Session(engine) as session:
                return _handle_new_intent(
                    session, user_id, conversation_id, intent
                )
    logger.warning(
        "구독 도구 결과 형식 오류: tool=%s artifact=%s",
        tool_message.name,
        artifact,
    )
    return _subscription_result(
        "구독 요청을 처리하는 중 도구 결과를 확인하지 못했습니다. "
        "다시 시도해 주세요."
    )
