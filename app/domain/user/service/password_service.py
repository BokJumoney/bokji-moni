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


def needs_rehash(password_hash: str) -> bool:
    """해시 설정이 강화된 경우 점진적 재해시 필요 여부를 반환한다."""
    return _password_hash.needs_update(password_hash)