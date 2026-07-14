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