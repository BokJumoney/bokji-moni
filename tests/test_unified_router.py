"""통합 라우터의 상태 우선순위와 안전한 실패 처리를 검증한다."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.domain.chat.graph.router.unified_router import UnifiedRoute, unified_router


class UnifiedRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_subscription_workflow_skips_llm(self):
        invoke = AsyncMock()
        with patch(
            "app.domain.chat.graph.router.unified_router._route_chain",
            new=SimpleNamespace(ainvoke=invoke),
        ):
            result = await unified_router(
                {
                    "question": "2번",
                    "conversation_mode": "subscription",
                    "conversation_id": "conversation-1",
                }
            )

        self.assertEqual("subscription", result["route"])
        self.assertEqual("active_workflow", result["route_source"])
        invoke.assert_not_awaited()

    async def test_application_workflow_skips_llm(self):
        invoke = AsyncMock()
        with patch(
            "app.domain.chat.graph.router.unified_router._route_chain",
            new=SimpleNamespace(ainvoke=invoke),
        ):
            result = await unified_router(
                {
                    "question": "네",
                    "conversation_mode": "application",
                    "conversation_id": "conversation-2",
                }
            )

        self.assertEqual("application", result["route"])
        invoke.assert_not_awaited()

    async def test_new_question_uses_llm_once(self):
        mocked = AsyncMock(return_value=UnifiedRoute(route="vectorstore"))
        with patch(
            "app.domain.chat.graph.router.unified_router._route_chain",
            new=SimpleNamespace(ainvoke=mocked),
        ):
            result = await unified_router(
                {
                    "question": "청년 지원 정책 알려줘",
                    "conversation_mode": "general",
                    "chat_history": [],
                }
            )

        self.assertEqual("vectorstore", result["route"])
        self.assertEqual("llm", result["route_source"])
        mocked.assert_awaited_once()

    async def test_llm_failure_uses_safe_route(self):
        mocked = AsyncMock(side_effect=RuntimeError("router unavailable"))
        with patch(
            "app.domain.chat.graph.router.unified_router._route_chain",
            new=SimpleNamespace(ainvoke=mocked),
        ):
            result = await unified_router(
                {"question": "알림 등록", "conversation_mode": "general"}
            )

        self.assertEqual("casual_talk", result["route"])


if __name__ == "__main__":
    unittest.main()
