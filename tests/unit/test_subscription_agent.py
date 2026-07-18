"""구독 에이전트의 Tool Calling 경계 테스트."""

import asyncio
import uuid
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from app.domain.subscription.exceptions import SubscriptionStorageError
from app.domain.subscription.agent.schemas import (
    EmptyToolInput,
    SubscriptionExecutionContext,
)
from app.domain.subscription.agent.tool_loop import SubscriptionToolLoop
from app.domain.subscription.agent.tools import build_subscription_tools
from app.domain.subscription.service.subscription_service import (
    SubscriptionApplicationService,
)


def test_tool_schemas_do_not_expose_user_id():
    tools = build_subscription_tools(
        SubscriptionExecutionContext(user_id=uuid.uuid4())
    )
    tool_map = {tool.name: tool for tool in tools}

    assert "list_my_subscriptions" in tool_map
    assert "get_my_notification_preferences" in tool_map
    assert "user_id" not in str(
        [tool.args_schema.model_json_schema() for tool in tools]
    )


def test_tool_loop_requires_and_executes_one_tool(monkeypatch):
    calls = {}

    def read_tool() -> str:
        calls["executed"] = True
        return "조회 결과"

    tool = StructuredTool.from_function(
        func=read_tool,
        name="read_tool",
        description="테스트 조회 도구",
        args_schema=EmptyToolInput,
    )

    class FakeBoundLlm:
        async def ainvoke(self, _messages):
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "read_tool",
                        "args": {},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            )

    class FakeLlm:
        def bind_tools(self, tools, **kwargs):
            calls["tool_choice"] = kwargs.get("tool_choice")
            calls["bound_tools"] = [item.name for item in tools]
            return FakeBoundLlm()

    monkeypatch.setattr(
        "app.domain.subscription.agent.tool_loop.get_llm_gpt",
        lambda: FakeLlm(),
    )

    result = asyncio.run(
        SubscriptionToolLoop().run("내 구독 보여줘", [tool])
    )
    assert result == "조회 결과"
    assert calls == {
        "tool_choice": "required",
        "bound_tools": ["read_tool"],
        "executed": True,
    }


@pytest.mark.parametrize(
    "operation",
    [
        lambda service, user_id: service.get_settings(user_id),
        lambda service, user_id: service.list_subscriptions(user_id),
        lambda service, user_id: service.find_policy_candidates("정책"),
        lambda service, user_id: service.find_subscription_candidates(
            user_id,
            "정책",
        ),
    ],
)
def test_repository_failures_are_normalized(operation):
    session = MagicMock()
    service = SubscriptionApplicationService(session)
    service.repository = MagicMock()
    service.repository.get_settings.side_effect = RuntimeError("db detail")
    service.repository.list_subscriptions.side_effect = RuntimeError("db detail")
    service.repository.find_policy_candidates.side_effect = RuntimeError("db detail")
    service.repository.find_subscription_candidates.side_effect = RuntimeError(
        "db detail"
    )

    with pytest.raises(SubscriptionStorageError) as exc_info:
        operation(service, uuid.uuid4())

    assert "db detail" not in str(exc_info.value)
    session.rollback.assert_called()


@pytest.mark.parametrize(
    ("repository_method", "operation"),
    [
        (
            "get_settings_for_update",
            lambda service, user_id: service.update_policy_news(user_id, False),
        ),
        (
            "get_subscription",
            lambda service, user_id: service.subscribe(
                user_id,
                "WLF-ERROR",
                "오류 정책",
            ),
        ),
        (
            "delete_subscription",
            lambda service, user_id: service.unsubscribe(
                user_id,
                "WLF-ERROR",
            ),
        ),
    ],
)
def test_mutation_repository_failures_are_normalized(
    repository_method,
    operation,
):
    session = MagicMock()
    service = SubscriptionApplicationService(session)
    service.repository = MagicMock()
    getattr(service.repository, repository_method).side_effect = RuntimeError(
        "db detail"
    )

    with pytest.raises(SubscriptionStorageError) as exc_info:
        operation(service, uuid.uuid4())

    assert "db detail" not in str(exc_info.value)
    session.rollback.assert_called()
