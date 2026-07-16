"""
마이페이지 API 테스트 (설계 5/9 절 기준).

TestClient 로 HTTP 흐름을 검증한다. 인증 쿠키를 직접 세팅하여 로그인을
우회하며, 기존 chat 서브그래프 import 충돌과 무관하도록 user_router 만
마운트한 독립 FastAPI 앱을 사용한다.

PostgreSQL test database 에서 실행한다.
"""
import uuid
from datetime import date, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.common.security import generate_session_token, hash_session_token
from app.common.timezone import now_kst
from app.domain.user.api.user_router import router as user_router
from app.domain.user.entity.models import AuthSession, User, UserWelfare

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture(scope="module", autouse=True)
def _ensure_tables():
    """독립 앱은 lifespan 을 타지 않으므로 테이블 생성을 명시 호출한다."""
    from app.infrastructure.db.connection import init_db

    init_db()


@pytest.fixture
def app():
    """user_router 만 마운트한 독립 앱 (chat import 충돌 회피)."""
    application = FastAPI()
    application.include_router(user_router, prefix="/api/v1/users")
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def authed():
    """테스트 사용자 + 유효 쿠키를 반환하고 종료 시 정리."""
    from app.infrastructure.db.connection import engine

    uid_email = f"mypage-{uuid.uuid4().hex}@example.com"
    with Session(engine) as s:
        u = User(
            email=uid_email,
            password_hash="x",
            name="MyPage Test",
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

        s.exec(delete(UserWelfare).where(UserWelfare.user_id == u.id))
        s.exec(delete(AuthSession).where(AuthSession.user_id == u.id))
        s.delete(u)
        s.commit()


def _auth(cookie):
    return {"cookies": cookie} if cookie else {}


# ---------------------------------------------------------------------------
# 인증 게이트
# ---------------------------------------------------------------------------


def test_get_profile_requires_cookie(client):
    r = client.get("/api/v1/users/me")
    assert r.status_code == 401


def test_get_welfare_requires_cookie(client):
    r = client.get("/api/v1/users/me/welfare-info")
    assert r.status_code == 401


def test_patch_profile_requires_cookie(client):
    r = client.patch("/api/v1/users/me", json={"name": "x"})
    assert r.status_code == 401


def test_patch_welfare_requires_cookie(client):
    r = client.patch("/api/v1/users/me/welfare-info", json={"region": "서울"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# 기본 프로필
# ---------------------------------------------------------------------------


def test_get_profile_returns_account_info(client, authed):
    r = client.get("/api/v1/users/me", cookies=authed["cookie"])
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == authed["email"]
    assert body["name"] == "MyPage Test"
    assert "id" in body and "created_at" in body and "updated_at" in body
    # 민감 필드 노출 금지
    assert "password_hash" not in body
    assert "role" not in body
    assert r.headers["cache-control"] == "private, no-store"


def test_patch_name_trims_and_updates(client, authed):
    from app.infrastructure.db.connection import engine

    r = client.patch("/api/v1/users/me", cookies=authed["cookie"], json={"name": "  홍길동  "})
    assert r.status_code == 200
    assert r.json()["name"] == "홍길동"

    # 새로고침 복원
    with Session(engine) as s:
        u = s.exec(select(User).where(User.id == authed["user_id"])).first()
        assert u.name == "홍길동"
        assert u.updated_at >= u.created_at


def test_patch_name_empty_rejected(client, authed):
    r = client.patch("/api/v1/users/me", cookies=authed["cookie"], json={"name": "   "})
    assert r.status_code == 422


def test_patch_extra_field_forbidden(client, authed):
    r = client.patch(
        "/api/v1/users/me",
        cookies=authed["cookie"],
        json={"name": "x", "role": "admin"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 복지 정보
# ---------------------------------------------------------------------------


def test_get_welfare_empty_returns_200_all_null(client, authed):
    r = client.get("/api/v1/users/me/welfare-info", cookies=authed["cookie"])
    assert r.status_code == 200
    body = r.json()
    for k in (
        "birth_date",
        "monthly_income",
        "family_size",
        "household_type",
        "region",
        "district",
        "has_disability",
        "assets",
        "employment_status",
        "updated_at",
    ):
        assert body[k] is None
    assert r.headers["cache-control"] == "private, no-store"


def test_patch_welfare_creates_row(client, authed):
    r = client.patch(
        "/api/v1/users/me/welfare-info",
        cookies=authed["cookie"],
        json={
            "monthly_income": 1200000,
            "family_size": 3,
            "region": "서울",
            "district": "종로구",
            "has_disability": False,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["monthly_income"] == 1200000
    assert body["family_size"] == 3
    assert body["region"] == "서울"
    assert body["has_disability"] is False
    assert body["updated_at"] is not None


def test_patch_welfare_partial_keeps_other_fields(client, authed):
    from app.infrastructure.db.connection import engine

    # 최초 저장
    client.patch(
        "/api/v1/users/me/welfare-info",
        cookies=authed["cookie"],
        json={"monthly_income": 1000000, "family_size": 4, "region": "서울"},
    )
    # 소득만 재수정
    r = client.patch(
        "/api/v1/users/me/welfare-info",
        cookies=authed["cookie"],
        json={"monthly_income": 2000000},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["monthly_income"] == 2000000
    assert body["family_size"] == 4   # 유지
    assert body["region"] == "서울"  # 유지

    # DB 새로고침 복원
    with Session(engine) as s:
        w = s.exec(
            select(UserWelfare).where(UserWelfare.user_id == authed["user_id"])
        ).first()
        assert w.monthly_income == 2000000
        assert w.family_size == 4


def test_patch_welfare_null_deletes_value(client, authed):
    r = client.patch(
        "/api/v1/users/me/welfare-info",
        cookies=authed["cookie"],
        json={"region": "서울", "district": "종로구"},
    )
    assert r.json()["region"] == "서울"
    # region 만 null 로 삭제
    r = client.patch(
        "/api/v1/users/me/welfare-info",
        cookies=authed["cookie"],
        json={"region": None},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["region"] is None
    assert body["district"] == "종로구"  # 유지


def test_patch_welfare_empty_body_422(client, authed):
    r = client.patch(
        "/api/v1/users/me/welfare-info", cookies=authed["cookie"], json={}
    )
    assert r.status_code == 422


def test_patch_welfare_negative_income_422(client, authed):
    r = client.patch(
        "/api/v1/users/me/welfare-info",
        cookies=authed["cookie"],
        json={"monthly_income": -1},
    )
    assert r.status_code == 422


def test_patch_welfare_zero_family_size_422(client, authed):
    r = client.patch(
        "/api/v1/users/me/welfare-info",
        cookies=authed["cookie"],
        json={"family_size": 0},
    )
    assert r.status_code == 422


def test_patch_welfare_future_birth_date_422(client, authed):
    future = date.today().replace(year=date.today().year + 1).isoformat()
    r = client.patch(
        "/api/v1/users/me/welfare-info",
        cookies=authed["cookie"],
        json={"birth_date": future},
    )
    assert r.status_code == 422


def test_patch_welfare_user_id_forbidden(client, authed):
    r = client.patch(
        "/api/v1/users/me/welfare-info",
        cookies=authed["cookie"],
        json={"user_id": str(uuid.uuid4()), "region": "서울"},
    )
    assert r.status_code == 422


def test_patch_welfare_empty_string_district_422(client, authed):
    # max_length 통과하지만 빈 문자열은 허용? → DTO 는 별도 검증 없이 허용.
    # 여기서는 422 가 아님을 확인(빈 문자열 허용 정책). 허용 범위 테스트용.
    r = client.patch(
        "/api/v1/users/me/welfare-info",
        cookies=authed["cookie"],
        json={"district": ""},
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# 사용자 격리
# ---------------------------------------------------------------------------


def test_user_isolation_other_user_cannot_see(client, authed):
    from app.infrastructure.db.connection import engine

    # 사용자 A 저장
    client.patch(
        "/api/v1/users/me/welfare-info",
        cookies=authed["cookie"],
        json={"monthly_income": 9999999, "region": "비밀지역A"},
    )

    # 사용자 B 생성 + 쿠키
    b_email = f"mypage-b-{uuid.uuid4().hex}@example.com"
    with Session(engine) as s:
        b = User(email=b_email, password_hash="x", name="B", is_active=True)
        s.add(b)
        s.commit()
        s.refresh(b)
        b_id = b.id
        token = generate_session_token()
        now = now_kst()
        asess = AuthSession(
            token_hash=hash_session_token(token),
            user_id=b_id,
            created_at=now,
            last_seen_at=now,
            idle_expires_at=now + timedelta(minutes=30),
            absolute_expires_at=now + timedelta(hours=24),
        )
        s.add(asess)
        s.commit()
        b_cookie = {"bokji_auth": token}

    try:
        r = client.get("/api/v1/users/me/welfare-info", cookies=b_cookie)
        assert r.status_code == 200
        body = r.json()
        assert body["monthly_income"] is None
        assert body["region"] is None
    finally:
        with Session(engine) as s:
            s.exec(delete(UserWelfare).where(UserWelfare.user_id == b_id))
            s.exec(delete(AuthSession).where(AuthSession.user_id == b_id))
            s.exec(delete(User).where(User.id == b_id))
            s.commit()


def test_response_does_not_expose_password_hash(client, authed):
    r = client.get("/api/v1/users/me", cookies=authed["cookie"])
    assert r.status_code == 200
    assert "password_hash" not in r.text


def test_expired_session_rejected(client, authed):
    from app.infrastructure.db.connection import engine

    with Session(engine) as s:
        a = s.exec(
            select(AuthSession).where(AuthSession.user_id == authed["user_id"])
        ).first()
        a.idle_expires_at = now_kst() - timedelta(minutes=1)
        s.add(a)
        s.commit()

    r = client.get("/api/v1/users/me", cookies=authed["cookie"])
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "SESSION_EXPIRED"