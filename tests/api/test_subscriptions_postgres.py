"""Docker PostgreSQL에서 실행하는 구독 통합 테스트.

실행 예:
    TEST_DATABASE_URL=postgresql+psycopg://... pytest \
        tests/api/test_subscriptions_postgres.py

환경 변수가 없으면 일반 테스트 실행에서는 건너뛴다.
"""

import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from sqlalchemy import delete
from sqlmodel import SQLModel, Session, create_engine, select

from app.domain.chat.graph.nodes.subscription_agent import subscription_agent
from app.domain.subscription.api.subscription_router import (
    router as subscription_router,
)
from app.domain.subscription.entity.models import (
    PolicySubscription,
    SubscriptionSettings,
)
from app.domain.subscription.service.subscription_service import (
    SubscriptionApplicationService,
)
from app.domain.user.dependencies import get_current_user
from app.domain.user.entity.models import User
from app.domain.welfare.entity.models import WelfarePolicy
from app.infrastructure.db.connection import get_session

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL이 설정된 PostgreSQL 통합 테스트에서만 실행",
)


@pytest.fixture(scope="module")
def pg_engine():
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    SQLModel.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            WelfarePolicy.__table__,
            SubscriptionSettings.__table__,
            PolicySubscription.__table__,
        ],
    )
    yield engine
    engine.dispose()


@pytest.fixture
def pg_api(pg_engine):
    marker = uuid.uuid4().hex
    users = {
        "a": User(
            email=f"subscription-pg-a-{marker}@example.com",
            password_hash="x",
            name="Postgres A",
        ),
        "b": User(
            email=f"subscription-pg-b-{marker}@example.com",
            password_hash="x",
            name="Postgres B",
        ),
    }
    with Session(pg_engine, expire_on_commit=False) as session:
        session.add_all(users.values())
        session.commit()

    def override_session():
        with Session(pg_engine) as session:
            yield session

    def override_user(request: Request) -> User:
        return users[request.headers.get("x-test-user", "a")]

    app = FastAPI()
    app.include_router(subscription_router)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_user

    with TestClient(app) as client:
        yield client, users

    with Session(pg_engine) as session:
        user_ids = [user.id for user in users.values()]
        session.exec(
            delete(PolicySubscription).where(
                PolicySubscription.user_id.in_(user_ids)
            )
        )
        session.exec(
            delete(SubscriptionSettings).where(
                SubscriptionSettings.user_id.in_(user_ids)
            )
        )
        session.exec(delete(User).where(User.id.in_(user_ids)))
        session.commit()


def test_postgres_api_contract_and_isolation(pg_api, pg_engine):
    client, users = pg_api

    response = client.get("/api/v1/subscriptions/settings")
    assert response.status_code == 200
    assert response.json()["policy_news_enabled"] is True
    assert response.json()["is_paused"] is False
    assert response.json()["updated_at"].endswith("+09:00")

    response = client.put(
        "/api/v1/subscriptions/settings/policy-news",
        json={"enabled": False},
    )
    assert response.status_code == 200
    assert response.json()["policy_news_enabled"] is False
    assert response.json()["is_paused"] is False

    response = client.put(
        "/api/v1/subscriptions/settings/pause",
        json={"paused": True},
    )
    assert response.status_code == 200
    assert response.json()["policy_news_enabled"] is False
    assert response.json()["is_paused"] is True

    with Session(pg_engine) as session:
        service = SubscriptionApplicationService(session)
        item = service.subscribe(
            users["a"].id,
            "WLF-2026-001",
            "청년 주거비 지원",
        )
        # 같은 사용자·정책 구독은 UNIQUE 제약과 서비스 양쪽에서 멱등 처리한다.
        duplicate = service.subscribe(
            users["a"].id,
            "WLF-2026-001",
            "청년 주거비 지원",
        )
        assert duplicate.id == item.id

        row = session.exec(
            select(PolicySubscription).where(PolicySubscription.id == item.id)
        ).one()
        row.application_deadline = date(2026, 8, 31)
        session.add(row)
        session.commit()

        service.subscribe(
            users["b"].id,
            "WLF-2026-002",
            "다른 사용자 정책",
        )

    response = client.get("/api/v1/subscriptions")
    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": item.id,
                "service_id": "WLF-2026-001",
                "service_name": "청년 주거비 지원",
                "application_deadline": "2026-08-31",
                "created_at": response.json()["items"][0]["created_at"],
            }
        ]
    }
    assert response.json()["items"][0]["created_at"].endswith("+09:00")

    # 다른 사용자의 같은 URL을 삭제해도 현재 사용자 범위 밖 행은 남는다.
    assert client.delete("/api/v1/subscriptions/WLF-2026-002").status_code == 204
    other_items = client.get(
        "/api/v1/subscriptions",
        headers={"x-test-user": "b"},
    ).json()["items"]
    assert [row["service_id"] for row in other_items] == ["WLF-2026-002"]

    assert client.delete("/api/v1/subscriptions/WLF-2026-001").status_code == 204
    assert client.get("/api/v1/subscriptions").json() == {"items": []}


def test_postgres_policy_candidate_query_deduplicates_chunks(pg_api, pg_engine):
    _, _ = pg_api
    marker = uuid.uuid4().hex[:8]
    service_id = f"WLF-PG-{marker}"
    service_name = f"Postgres 후보 정책 {marker}"

    with Session(pg_engine) as session:
        session.add_all(
            [
                WelfarePolicy(
                    service_id=service_id,
                    service_name=service_name,
                    chunk_type="기본정보",
                    page_content="기본정보",
                ),
                WelfarePolicy(
                    service_id=service_id,
                    service_name=service_name,
                    chunk_type="신청",
                    page_content="신청정보",
                ),
            ]
        )
        session.commit()

        candidates = SubscriptionApplicationService(
            session
        ).find_policy_candidates(service_id)
        assert candidates == [(service_id, service_name)]

        session.exec(
            delete(WelfarePolicy).where(WelfarePolicy.service_id == service_id)
        )
        session.commit()


def test_postgres_user_delete_cascades_new_tables(pg_api, pg_engine):
    _, users = pg_api
    user_id = users["a"].id

    with Session(pg_engine) as session:
        service = SubscriptionApplicationService(session)
        service.get_settings(user_id)
        service.subscribe(user_id, "WLF-CASCADE", "Cascade 정책")

        user = session.get(User, user_id)
        session.delete(user)
        session.commit()

        assert session.get(SubscriptionSettings, user_id) is None
        assert session.exec(
            select(PolicySubscription).where(
                PolicySubscription.user_id == user_id
            )
        ).first() is None


def test_subscription_agent_read_uses_tool_calling(
    pg_api,
    pg_engine,
    monkeypatch,
):
    _, users = pg_api
    with Session(pg_engine) as session:
        SubscriptionApplicationService(session).subscribe(
            users["a"].id,
            "WLF-TOOL-001",
            "Tool Calling 정책",
        )

    captured = {}

    class FakeBoundLlm:
        async def ainvoke(self, _messages):
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "list_my_subscriptions",
                        "args": {},
                        "id": "call-postgres-read",
                        "type": "tool_call",
                    }
                ],
            )

    class FakeLlm:
        def bind_tools(self, tools, **kwargs):
            captured["tool_choice"] = kwargs.get("tool_choice")
            captured["tool_names"] = [tool.name for tool in tools]
            return FakeBoundLlm()

    monkeypatch.setattr(
        "app.domain.subscription.agent.tool_loop.get_llm_gpt",
        lambda: FakeLlm(),
    )
    result = asyncio.run(
        subscription_agent(
            {"question": "내가 구독한 정책 목록을 보여줘"},
            {"configurable": {"user_id": str(users["a"].id)}},
        )
    )

    assert captured["tool_choice"] == "required"
    assert "list_my_subscriptions" in captured["tool_names"]
    assert "Tool Calling 정책" in result["answer"]


def test_postgres_concurrent_first_updates_and_duplicate_subscribe(
    pg_api,
    pg_engine,
):
    _, users = pg_api
    user_id = users["a"].id
    update_barrier = Barrier(2)

    def update_news():
        with Session(pg_engine) as session:
            update_barrier.wait()
            return SubscriptionApplicationService(session).update_policy_news(
                user_id,
                False,
            )

    def update_pause():
        with Session(pg_engine) as session:
            update_barrier.wait()
            return SubscriptionApplicationService(session).update_pause(
                user_id,
                True,
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        news_future = executor.submit(update_news)
        pause_future = executor.submit(update_pause)
        update_results = [news_future.result(), pause_future.result()]

    with Session(pg_engine) as session:
        final_settings = SubscriptionApplicationService(session).get_settings(
            user_id
        )
    assert final_settings.policy_news_enabled is False
    assert final_settings.is_paused is True
    assert final_settings.updated_at >= max(
        result.updated_at for result in update_results
    )

    subscribe_barrier = Barrier(2)

    def subscribe_once():
        with Session(pg_engine) as session:
            subscribe_barrier.wait()
            return SubscriptionApplicationService(session).subscribe(
                user_id,
                "WLF-CONCURRENT",
                "동시 구독 정책",
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(subscribe_once)
        second_future = executor.submit(subscribe_once)
        first = first_future.result()
        second = second_future.result()

    assert first.id == second.id
    with Session(pg_engine) as session:
        rows = session.exec(
            select(PolicySubscription).where(
                PolicySubscription.user_id == user_id,
                PolicySubscription.service_id == "WLF-CONCURRENT",
            )
        ).all()
    assert len(rows) == 1
