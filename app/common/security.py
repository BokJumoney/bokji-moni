"""
인증 보조 순수 함수.

- 이메일 정규화
- 세션 토큰 생성/해시

비밀번호 해시는 pwdlib 경계인 password_service.py 에서 다룬다.
여기서는 비밀번호 평문을 다루지 않는다.
"""
import hashlib
import secrets


def normalize_email(email: str) -> str:
    """
    이메일을 일관된 규칙으로 정규화한다.

    - 앞뒤 공백 제거
    - 전체 소문자화 (로컬/도메인 동일 규칙)
    - 내부 공백 제거
    """
    return email.strip().lower().replace(" ", "")


def generate_session_token() -> str:
    """충분한 엔트로피의 무작위 세션 토큰을 생성한다."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """
    세션 토큰의 SHA-256 hex 해시를 반환한다.

    원본 토큰은 쿠키에만, DB에는 해시만 저장한다.
    비밀번호에는 절대 같은 방식을 사용하지 않는다.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def build_session_cookie(token: str) -> dict:
    """
    설정에 따라 세션 쿠키 옵션 dict를 반환한다.

    - 개발: `bokji_auth`
    - 운영: `__Host-bokji_auth` (Domain 미설정, host-only)
    - response.set_cookie(**return_value) 로 사용한다.
    """
    from app.infrastructure.config import settings as _settings

    name = _settings.SESSION_COOKIE_NAME
    if _settings.APP_ENV == "production":
        name = f"__Host-{name}"

    return {
        "key": name,
        "value": token,
        "httponly": True,
        "secure": _settings.SESSION_COOKIE_SECURE,
        "samesite": _settings.SESSION_COOKIE_SAMESITE,
        "path": "/",
    }


def build_session_delete_cookie() -> dict:
    """
    세션 쿠키 삭제 옵션 dict를 반환한다.

    로그아웃 시 동일 속성으로 빈 값·만료 쿠키를 설정할 때 사용한다.
    """
    from app.infrastructure.config import settings as _settings

    name = _settings.SESSION_COOKIE_NAME
    if _settings.APP_ENV == "production":
        name = f"__Host-{name}"

    return {
        "key": name,
        "value": "",
        "httponly": True,
        "secure": _settings.SESSION_COOKIE_SECURE,
        "samesite": _settings.SESSION_COOKIE_SAMESITE,
        "path": "/",
        "max_age": 0,
    }