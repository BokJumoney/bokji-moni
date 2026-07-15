"""
채팅 세션 목록 API 테스트 (설계명세서 13.3).

TestClient 로 실제 HTTP 흐름을 검증한다. 인증 쿠키를 직접 세팅하여
로그인 절차를 우회한다 (인증 자체는 별도 테스트 영역).
"""
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.common.security import generate_session_token, hash_session_token
from app.common.timezone import now_kst
from app.domain.chat.entity.models import Conversation
from app.domain.chat.repository import ConversationRepository
from app.domain.chat.utils import normalize_title
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

    uid_email = f"api-{uuid.uuid4().hex}@example.com"
    with Session(engine) as s:
        u = User(
            email=uid_email,
            password_hash="x",
            name="API Test",
            is_active=True,
        )
        s.add(u)
        s.commit()
        s.refresh(u)

        token = generate_session_token()
        now = now_kst()
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

        s.exec(delete(Conversation).where(Conversation.user_id == u.id))
        s.exec(delete(AuthSession).where(AuthSession.user_id == u.id))
        s.delete(u)
        s.commit()


def _seed_conversations(user_id, n, repo=None):
    from app.infrastructure.db.connection import engine

    if repo is None:
        repo = ConversationRepository(Session(engine))
    for i in range(n):
        c = repo.create_conversation(user_id, normalize_title(f"제목{i}"))
        repo.add_message(c, "user", f"내용{i}")


def test_no_cookie_returns_401(client):
    r = client.get("/api/v1/chat/sessions")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


def test_empty_list(client, authed):
    r = client.get("/api/v1/chat/sessions", cookies=authed["cookie"])
    assert r.status_code == 200
    body = r.json()
    assert body == {"items": [], "next_cursor": None, "has_more": False}
    assert r.headers["cache-control"] == "private, no-store"


def test_list_returns_user_conversations(client, authed):
    _seed_conversations(authed["user_id"], 2)
    r = client.get("/api/v1/chat/sessions", cookies=authed["cookie"])
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 2
    item = items[0]
    for key in (
        "session_id",
        "title",
        "last_message_preview",
        "message_count",
        "created_at",
        "last_message_at",
    ):
        assert key in item
    assert item["message_count"] == 1


def test_pagination(client, authed):
    _seed_conversations(authed["user_id"], 25)
    r1 = client.get(
        "/api/v1/chat/sessions?limit=20", cookies=authed["cookie"]
    )
    assert r1.status_code == 200
    b1 = r1.json()
    assert len(b1["items"]) == 20
    assert b1["has_more"] is True
    assert b1["next_cursor"] is not None

    r2 = client.get(
        f"/api/v1/chat/sessions?limit=20&cursor={b1['next_cursor']}",
        cookies=authed["cookie"],
    )
    assert r2.status_code == 200
    b2 = r2.json()
    assert len(b2["items"]) == 5
    assert b2["has_more"] is False
    assert b2["next_cursor"] is None

    ids1 = {it["session_id"] for it in b1["items"]}
    ids2 = {it["session_id"] for it in b2["items"]}
    assert ids1.isdisjoint(ids2)


def test_invalid_cursor_422(client, authed):
    r = client.get(
        "/api/v1/chat/sessions?cursor=!!!bad", cookies=authed["cookie"]
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "INVALID_CURSOR"


def test_limit_bounds(client, authed):
    assert (
        client.get(
            "/api/v1/chat/sessions?limit=0", cookies=authed["cookie"]
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/v1/chat/sessions?limit=51", cookies=authed["cookie"]
        ).status_code
        == 422
    )


def test_expired_session_401(client, authed):
    from app.infrastructure.db.connection import engine

    with Session(engine) as s:
        a = s.exec(
            select(AuthSession).where(AuthSession.user_id == authed["user_id"])
        ).first()
        a.idle_expires_at = now_kst() - timedelta(minutes=1)
        s.add(a)
        s.commit()
    r = client.get("/api/v1/chat/sessions", cookies=authed["cookie"])
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "SESSION_EXPIRED"


def test_other_user_not_exposed(client, authed):
    _seed_conversations(authed["user_id"], 3)
    # 다른 사용자 추가
    other_email = f"other-{uuid.uuid4().hex}@example.com"
    from app.infrastructure.db.connection import engine

    with Session(engine) as s:
        other = User(email=other_email, password_hash="x", name="Other")
        s.add(other)
        s.commit()
        s.refresh(other)
        other_id = other.id
    _seed_conversations(other_id, 5)
    r = client.get("/api/v1/chat/sessions", cookies=authed["cookie"])
    items = r.json()["items"]
    assert len(items) == 3
    # 정리
    with Session(engine) as s:
        s.exec(delete(Conversation).where(Conversation.user_id == other_id))
        o = s.exec(select(User).where(User.id == other_id)).first()
        if o:
            s.delete(o)
        s.commit()


def test_delete_session_removes_from_list(client, authed):
    _seed_conversations(authed["user_id"], 1)
    r = client.get("/api/v1/chat/sessions", cookies=authed["cookie"])
    sid = r.json()["items"][0]["session_id"]
    d = client.delete(f"/api/v1/chat/sessions/{sid}", cookies=authed["cookie"])
    assert d.status_code == 204
    r2 = client.get("/api/v1/chat/sessions", cookies=authed["cookie"])
    assert r2.json()["items"] == []


def test_history_not_found_for_foreign_session(client, authed):
    foreign_id = uuid.uuid4()
    r = client.get(
        f"/api/v1/chat/sessions/{foreign_id}/history", cookies=authed["cookie"]
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "CHAT_SESSION_NOT_FOUND"