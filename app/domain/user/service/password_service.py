"""
비밀번호 해시/검증 경계 (pwdlib Argon2id).

평문 비밀번호는 이 모듈 호출 범위를 벗어나
저장/로그/예외 메시지에 남기지 않는다.
"""
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

_password_hash = PasswordHash((Argon2Hasher(),))


def hash_password(password: str) -> str:
    """평문 비밀번호를 Argon2id 해시로 변환한다."""
    return _password_hash.hash(password)


def verify_password(password_plain: str, password_hash: str) -> bool:
    """평문 비밀번호와 해시를 검증한다. 일치하면 True."""
    return _password_hash.verify(password_plain, password_hash)


def verify_and_update(
    password_plain: str,
    password_hash: str,
) -> tuple[bool, str | None]:
    """
    비밀번호 검증 및 해시 설정 강화 시 재해시.

    Returns:
        (검증 성공 여부, 새 해시 | None)
        검증에 성공했고 해시 파라미터가 갱신되었으면 새 해시를 반환한다.
    """
    is_valid, updated_hash = _password_hash.verify_and_update(
        password_plain,
        password_hash,
    )
    return is_valid, updated_hash