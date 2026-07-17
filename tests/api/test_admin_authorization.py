"""관리자 API 권한 분리 테스트."""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.admin.api.admin_policy import router as admin_policy_router
from app.domain.admin.api.admin_router import (
    get_admin_file_service,
    router as admin_router,
)
from app.domain.user.dependencies import get_current_user
from app.domain.user.entity.models import UserRole
from app.infrastructure.db.connection import get_session

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


class _FakeFileService:
    def delete_file(self, file_id: str) -> dict:
        return {"fileId": file_id, "deleted": True}


class _FakePolicyResult:
    def mappings(self):
        return self

    def all(self):
        return [
            SimpleNamespace(
                policy_id="policy-1",
                policy_name=" 테스트 정책 ",
            )
        ]


class _FakeSession:
    def exec(self, _query):
        return _FakePolicyResult()


@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(admin_router)
    application.include_router(admin_policy_router)
    application.dependency_overrides[get_admin_file_service] = _FakeFileService
    application.dependency_overrides[get_session] = _FakeSession
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


def _set_role(app: FastAPI, role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role=role)


def test_admin_file_api_requires_login(client):
    response = client.delete(f"/admin/files/{'0' * 32}")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


def test_admin_file_api_rejects_normal_user(app, client):
    _set_role(app, UserRole.USER.value)

    response = client.delete(f"/admin/files/{'0' * 32}")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"


def test_admin_file_api_allows_admin(app, client):
    _set_role(app, UserRole.ADMIN.value)

    file_id = "0" * 32
    response = client.delete(f"/admin/files/{file_id}")

    assert response.status_code == 200
    assert response.json() == {"fileId": file_id, "deleted": True}


def test_admin_policy_api_rejects_normal_user(app, client):
    _set_role(app, UserRole.USER.value)

    response = client.get("/admin/policies")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"


def test_admin_policy_api_allows_admin(app, client):
    _set_role(app, UserRole.ADMIN.value)

    response = client.get("/admin/policies")

    assert response.status_code == 200
    assert response.json() == [{"id": "policy-1", "name": "테스트 정책"}]
