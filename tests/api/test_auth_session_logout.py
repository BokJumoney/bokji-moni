"""
인증 /session, /logout API 테스트.

TestClient 로 실제 HTTP 흐름을 검증한다. 인증 쿠키를 직접 세팅하여
로그인 절차를 우회한다 (로그인 자체는 별도 테스트 영역).
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.common.security import generate_session_token, hash_session_token
from app.domain.user.entity.models import AuthSession, User

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


@pytest.fixture
def authed():
    """테스트 사용자 + 유효 쿠키를 반환하고 종료 시 정리."""
    from app.infrastructure.db.connection import engine

    uid_email = f"auth-{uuid.uuid4().hex}@example.com"
    with Session(engine) as s:
        u = User(
            email=uid_email,
            password_hash="x",
            name="Auth Test",
            is_active=True,
        )
        s.add(u)
        s.commit()
        s.refresh(u)

        token = generate_session_token()
        now = datetime.now(timezone.utc)
        asess = AuthSession(
            token_hash=hash_session_token(token),
            user_id=u.id,
            created_at=now,
            last_seen_at=now,
            idle_expires_at=now + timedelta(minutes=30),
            absolute_expires_at=now + timedelta(hours=24),
        )
        s.add(asess)
        s.commit()
        yield {"cookie": {"bokji_auth": token}, "user_id": u.id, "email": uid_email}

        s.exec(delete(AuthSession).where(AuthSession.user_id == u.id))
        s.delete(u)
        s.commit()


def test_session_requires_cookie(client):
    r = client.get("/api/v1/auth/session")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


def test_session_returns_user_and_expiry(client, authed):
    r = client.get("/api/v1/auth/session", cookies=authed["cookie"])
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == authed["email"]
    assert "idle_expires_at" in body
    assert "absolute_expires_at" in body
    assert r.headers["cache-control"] == "no-store"


def test_session_expired_401(client, authed):
    from app.infrastructure.db.connection import engine

    with Session(engine) as s:
        a = s.exec(
            select(AuthSession).where(AuthSession.user_id == authed["user_id"])
        ).first()
        a.idle_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        s.add(a)
        s.commit()
    r = client.get("/api/v1/auth/session", cookies=authed["cookie"])
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "SESSION_EXPIRED"


def test_logout_without_cookie_still_204(client):
    r = client.post("/api/v1/auth/logout")
    assert r.status_code == 204
    assert r.headers["cache-control"] == "no-store"
    # 삭제 쿠키가 set-cookie 에 포함되어 있는지 확인
    set_cookie = r.headers.get("set-cookie", "")
    assert "bokji_auth=" in set_cookie


def test_logout_revokes_session_and_clears_cookie(client, authed):
    from app.infrastructure.db.connection import engine

    # logout 전 세션 유효
    assert client.get(
        "/api/v1/auth/session", cookies=authed["cookie"]
    ).status_code == 200

    r = client.post("/api/v1/auth/logout", cookies=authed["cookie"])
    assert r.status_code == 204

    # 로그아웃 후 동일 쿠키로 /session 호출 시 401
    assert client.get(
        "/api/v1/auth/session", cookies=authed["cookie"]
    ).status_code == 401

    # DB 상에서 세션이 폐기되었는지 확인
    with Session(engine) as s:
        a = s.exec(
            select(AuthSession).where(AuthSession.user_id == authed["user_id"])
        ).first()
        assert a.revoked_at is not None


def test_logout_idempotent(client, authed):
    r1 = client.post("/api/v1/auth/logout", cookies=authed["cookie"])
    assert r1.status_code == 204
    # 두 번째 logout (이미 쿠키는 무효 세션) 도 204
    r2 = client.post("/api/v1/auth/logout", cookies=authed["cookie"])
    assert r2.status_code == 204