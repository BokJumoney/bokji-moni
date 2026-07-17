"""구독 Tool Calling 경로와 활성 대화 우선순위를 검증한다."""

import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from app.common.timezone import now_kst
from app.domain.chat.entity.models import Conversation
from app.domain.chat.graph.nodes.subscription.agent import (
    list_policy_subscriptions,
)
from app.domain.chat.graph.subgraph.subscription_graph import subscription_graph
from app.domain.subscription.entity.models import (
    NotificationSettings,
    PolicySubscription,
    SubscriptionDialog,
)
from app.domain.user.entity.models import User
from app.domain.welfare.entity.models import WelfarePolicy


class SubscriptionToolGraphTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        for table in (
            User.__table__,
            Conversation.__table__,
            WelfarePolicy.__table__,
            PolicySubscription.__table__,
            NotificationSettings.__table__,
            SubscriptionDialog.__table__,
        ):
            table.create(self.engine, checkfirst=True)

        with Session(self.engine) as session:
            self.user = User(
                email="tool-test@example.com",
                password_hash="test",
                name="도구 테스트",
            )
            session.add(self.user)
            session.commit()
            session.refresh(self.user)
            self.conversation = Conversation(
                user_id=self.user.id,
                title="구독 도구 테스트",
            )
            self.policy = WelfarePolicy(
                service_id="TOOL-POLICY",
                service_name="도구 테스트 정책",
                department="테스트부",
                application_deadline=now_kst().date() + timedelta(days=30),
                page_content="테스트 본문",
            )
            session.add(self.conversation)
            session.add(self.policy)
            session.commit()
            session.refresh(self.conversation)
            session.refresh(self.policy)
            self.user_id = self.user.id
            self.conversation_id = self.conversation.id
            self.policy_id = self.policy.id

    def test_user_id_is_hidden_from_model_tool_schema(self):
        schema = list_policy_subscriptions.tool_call_schema.model_json_schema()
        self.assertNotIn("user_id", schema.get("properties", {}))

    async def test_list_request_executes_tool_with_injected_user(self):
        with Session(self.engine) as session:
            session.add(
                PolicySubscription(user_id=self.user_id, policy_id=self.policy_id)
            )
            session.commit()

        tool_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "list_policy_subscriptions",
                    "args": {},
                    "id": "tool-call-1",
                    "type": "tool_call",
                }
            ],
        )
        mocked_chain = SimpleNamespace(ainvoke=AsyncMock(return_value=tool_response))

        with (
            patch(
                "app.domain.chat.graph.nodes.subscription.agent.engine",
                self.engine,
            ),
            patch(
                "app.domain.chat.graph.nodes.subscription.agent._tool_chain",
                mocked_chain,
            ),
        ):
            result = await subscription_graph.ainvoke(
                {
                    "question": "내가 구독한 정책 보여줘",
                    "user_id": str(self.user_id),
                    "conversation_id": str(self.conversation_id),
                }
            )

        self.assertIn("도구 테스트 정책", result["generation"])
        self.assertEqual("subscription", result["route"])
        mocked_chain.ainvoke.assert_awaited_once()

    async def test_active_confirmation_skips_tool_selecting_llm(self):
        with Session(self.engine) as session:
            session.add(
                SubscriptionDialog(
                    conversation_id=self.conversation_id,
                    user_id=self.user_id,
                    action="subscribe",
                    stage="awaiting_confirmation",
                    policy_query="도구 테스트",
                    candidate_policy_ids=[self.policy_id],
                    selected_policy_id=self.policy_id,
                    expires_at=now_kst() + timedelta(minutes=30),
                )
            )
            session.commit()

        mocked_chain = SimpleNamespace(ainvoke=AsyncMock())
        with (
            patch(
                "app.domain.chat.graph.nodes.subscription.agent.engine",
                self.engine,
            ),
            patch(
                "app.domain.chat.graph.nodes.subscription.agent._tool_chain",
                mocked_chain,
            ),
        ):
            result = await subscription_graph.ainvoke(
                {
                    "question": "아니요",
                    "user_id": str(self.user_id),
                    "conversation_id": str(self.conversation_id),
                }
            )

        self.assertIn("요청을 취소", result["generation"])
        mocked_chain.ainvoke.assert_not_awaited()

    async def test_search_tool_creates_confirmation_dialog(self):
        tool_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_subscription_policies",
                    "args": {
                        "policy_query": "도구 테스트 정책",
                        "action": "subscribe",
                    },
                    "id": "tool-call-2",
                    "type": "tool_call",
                }
            ],
        )
        mocked_chain = SimpleNamespace(ainvoke=AsyncMock(return_value=tool_response))
        empty_retriever = SimpleNamespace(invoke=lambda _: [])

        with (
            patch(
                "app.domain.chat.graph.nodes.subscription.agent.engine",
                self.engine,
            ),
            patch(
                "app.domain.chat.graph.nodes.subscription.agent._tool_chain",
                mocked_chain,
            ),
            patch(
                "app.domain.chat.graph.nodes.subscription.agent.get_ensemble_retriever",
                return_value=empty_retriever,
            ),
        ):
            result = await subscription_graph.ainvoke(
                {
                    "question": "도구 테스트 정책 마감 알림 구독해줘",
                    "user_id": str(self.user_id),
                    "conversation_id": str(self.conversation_id),
                }
            )

        self.assertIn("구독하시겠어요", result["generation"])
        with Session(self.engine) as session:
            dialog = session.exec(select(SubscriptionDialog)).first()
            self.assertIsNotNone(dialog)
            self.assertEqual("awaiting_confirmation", dialog.stage)
            self.assertEqual(self.policy_id, dialog.selected_policy_id)

    async def test_specific_policy_request_corrects_global_setting_tool(self):
        """모델이 전역 설정을 골라도 정책명이 있으면 정책 검색으로 교정한다."""
        wrong_tool_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "request_notification_setting_change",
                    "args": {"action": "enable_policy_news"},
                    "id": "wrong-global-tool",
                    "type": "tool_call",
                }
            ],
        )
        mocked_chain = SimpleNamespace(
            ainvoke=AsyncMock(return_value=wrong_tool_response)
        )
        empty_retriever = SimpleNamespace(invoke=lambda _: [])

        with (
            patch(
                "app.domain.chat.graph.nodes.subscription.agent.engine",
                self.engine,
            ),
            patch(
                "app.domain.chat.graph.nodes.subscription.agent._tool_chain",
                mocked_chain,
            ),
            patch(
                "app.domain.chat.graph.nodes.subscription.agent.get_ensemble_retriever",
                return_value=empty_retriever,
            ),
        ):
            result = await subscription_graph.ainvoke(
                {
                    "question": "도구 테스트 정책에 대해서 알림을 보내줘",
                    "user_id": str(self.user_id),
                    "conversation_id": str(self.conversation_id),
                    "chat_history": [{"role": "assistant", "content": "이전 답변"}],
                }
            )

        self.assertIn("구독하시겠어요", result["generation"])
        called_input = mocked_chain.ainvoke.await_args.args[0]
        self.assertEqual(1, len(called_input["chat_history"]))
        with Session(self.engine) as session:
            dialog = session.exec(select(SubscriptionDialog)).first()
            settings = session.get(NotificationSettings, self.user_id)
            self.assertIsNotNone(dialog)
            self.assertIsNone(settings)

    async def test_ambiguous_pronoun_never_enables_global_setting(self):
        wrong_tool_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "request_notification_setting_change",
                    "args": {"action": "enable_policy_news"},
                    "id": "ambiguous-global-tool",
                    "type": "tool_call",
                }
            ],
        )
        mocked_chain = SimpleNamespace(
            ainvoke=AsyncMock(return_value=wrong_tool_response)
        )

        with (
            patch(
                "app.domain.chat.graph.nodes.subscription.agent.engine",
                self.engine,
            ),
            patch(
                "app.domain.chat.graph.nodes.subscription.agent._tool_chain",
                mocked_chain,
            ),
        ):
            result = await subscription_graph.ainvoke(
                {
                    "question": "이거 알림 보내줘",
                    "user_id": str(self.user_id),
                    "conversation_id": str(self.conversation_id),
                    "chat_history": [],
                }
            )

        self.assertIn("정책명을 알려주세요", result["generation"])
        with Session(self.engine) as session:
            self.assertIsNone(session.get(NotificationSettings, self.user_id))

    async def test_pronoun_resolves_policy_from_recent_history(self):
        wrong_tool_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "request_notification_setting_change",
                    "args": {"action": "enable_policy_news"},
                    "id": "history-global-tool",
                    "type": "tool_call",
                }
            ],
        )
        mocked_chain = SimpleNamespace(
            ainvoke=AsyncMock(return_value=wrong_tool_response)
        )
        empty_retriever = SimpleNamespace(invoke=lambda _: [])

        with (
            patch(
                "app.domain.chat.graph.nodes.subscription.agent.engine",
                self.engine,
            ),
            patch(
                "app.domain.chat.graph.nodes.subscription.agent._tool_chain",
                mocked_chain,
            ),
            patch(
                "app.domain.chat.graph.nodes.subscription.agent.get_ensemble_retriever",
                return_value=empty_retriever,
            ),
        ):
            result = await subscription_graph.ainvoke(
                {
                    "question": "이거 알림 보내줘",
                    "user_id": str(self.user_id),
                    "conversation_id": str(self.conversation_id),
                    "chat_history": [
                        {
                            "role": "assistant",
                            "content": "추천 정책은 **도구 테스트 정책**입니다.",
                        }
                    ],
                }
            )

        self.assertIn("구독하시겠어요", result["generation"])
        called_question = mocked_chain.ainvoke.await_args.args[0]["question"]
        self.assertIn("도구 테스트 정책", called_question)

    async def test_explicit_global_request_can_change_setting(self):
        tool_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "request_notification_setting_change",
                    "args": {"action": "enable_policy_news"},
                    "id": "explicit-global-tool",
                    "type": "tool_call",
                }
            ],
        )
        mocked_chain = SimpleNamespace(ainvoke=AsyncMock(return_value=tool_response))

        with (
            patch(
                "app.domain.chat.graph.nodes.subscription.agent.engine",
                self.engine,
            ),
            patch(
                "app.domain.chat.graph.nodes.subscription.agent._tool_chain",
                mocked_chain,
            ),
        ):
            result = await subscription_graph.ainvoke(
                {
                    "question": "신규·폐지 정책 소식을 전체 알림으로 보내줘",
                    "user_id": str(self.user_id),
                    "conversation_id": str(self.conversation_id),
                }
            )

        self.assertIn("받도록 설정", result["generation"])
        with Session(self.engine) as session:
            settings = session.get(NotificationSettings, self.user_id)
            self.assertTrue(settings.policy_news_enabled)


if __name__ == "__main__":
    unittest.main()
