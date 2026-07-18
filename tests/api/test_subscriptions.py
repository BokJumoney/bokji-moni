"""프런트 계약 기준 구독 API 테스트.

개발 PostgreSQL을 건드리지 않도록 임시 SQLite DB와 FastAPI dependency
override를 사용한다.
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

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
from app.infrastructure.db.connection import get_session


@pytest.fixture
def api() -> Generator[tuple[TestClient, object, dict[str, User]], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            SubscriptionSettings.__table__,
            PolicySubscription.__table__,
        ],
    )

    users = {
        "a": User(
            id=uuid.uuid4(),
            email=f"{uuid.uuid4()}@example.com",
            password_hash="x",
            name="A",
        ),
        "b": User(
            id=uuid.uuid4(),
            email=f"{uuid.uuid4()}@example.com",
            password_hash="x",
            name="B",
        ),
    }

    with Session(engine, expire_on_commit=False) as session:
        session.add_all(users.values())
        session.commit()

    def override_session():
        with Session(engine) as session:
            yield session

    def override_user(request: Request) -> User:
        return users[request.headers.get("x-test-user", "a")]

    app = FastAPI()
    app.include_router(subscription_router)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_user

    with TestClient(app) as client:
        yield client, engine, users


def test_settings_contract_and_full_put_response(api):
    client, _, _ = api

    response = client.get("/api/v1/subscriptions/settings")
    assert response.status_code == 200
    assert response.json()["policy_news_enabled"] is True
    assert response.json()["is_paused"] is False
    assert response.json()["updated_at"].endswith("+09:00")
    assert response.headers["cache-control"] == "private, no-store"

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
    assert set(response.json()) == {
        "policy_news_enabled",
        "is_paused",
        "updated_at",
    }


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/api/v1/subscriptions/settings/policy-news", {"enabled": "true"}),
        ("/api/v1/subscriptions/settings/policy-news", {"enabled": True, "x": 1}),
        ("/api/v1/subscriptions/settings/pause", {}),
    ],
)
def test_settings_reject_invalid_json(api, path, body):
    client, _, _ = api
    assert client.put(path, json=body).status_code == 422


def test_list_delete_and_user_isolation(api):
    client, engine, users = api

    with Session(engine) as session:
        service = SubscriptionApplicationService(session)
        service.subscribe(
            users["a"].id,
            "WLF-2026-001",
            "청년 주거비 지원",
        )
        service.subscribe(
            users["b"].id,
            "WLF-2026-002",
            "다른 사용자 정책",
        )

    response = client.get("/api/v1/subscriptions")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items"}
    assert len(body["items"]) == 1
    assert body["items"][0]["service_id"] == "WLF-2026-001"
    assert isinstance(body["items"][0]["id"], int)
    assert body["items"][0]["application_deadline"] is None
    assert body["items"][0]["created_at"].endswith("+09:00")

    response = client.delete("/api/v1/subscriptions/WLF-2026-002")
    assert response.status_code == 204
    assert response.content == b""
    assert len(
        client.get(
            "/api/v1/subscriptions",
            headers={"x-test-user": "b"},
        ).json()["items"]
    ) == 1

    response = client.delete("/api/v1/subscriptions/WLF-2026-001")
    assert response.status_code == 204
    assert client.get("/api/v1/subscriptions").json() == {"items": []}

    # 멱등 삭제
    assert (
        client.delete("/api/v1/subscriptions/WLF-2026-001").status_code
        == 204
    )


def test_all_endpoints_require_authentication(api):
    _, engine, _ = api

    def override_session():
        with Session(engine) as session:
            yield session

    def reject_user():
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTHENTICATION_REQUIRED",
                "message": "로그인이 필요합니다.",
            },
        )

    app = FastAPI()
    app.include_router(subscription_router)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = reject_user

    with TestClient(app) as client:
        requests = [
            client.get("/api/v1/subscriptions/settings"),
            client.put(
                "/api/v1/subscriptions/settings/policy-news",
                json={"enabled": True},
            ),
            client.put(
                "/api/v1/subscriptions/settings/pause",
                json={"paused": True},
            ),
            client.get("/api/v1/subscriptions"),
            client.delete("/api/v1/subscriptions/WLF-2026-001"),
        ]

    assert all(response.status_code == 401 for response in requests)
