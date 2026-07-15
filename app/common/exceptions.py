"""
인증 도메인 공통 예외.

모든 인증 관련 예외는 status_code/code/message 를 가져서
일관된 오류 응답 계약(9.4 오류 계약)을 만족한다.
"""


class AuthError(Exception):
    """인증 도메인 예외 베이스."""

    status_code: int = 400
    code: str = "AUTH_ERROR"
    message: str = "인증 오류가 발생했습니다."

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


class EmailAlreadyExistsError(AuthError):
    status_code = 409
    code = "EMAIL_ALREADY_EXISTS"
    message = "이미 사용 중인 이메일입니다."


class InvalidCredentialsError(AuthError):
    status_code = 401
    code = "INVALID_CREDENTIALS"
    message = "이메일 또는 비밀번호가 올바르지 않습니다."


class AuthenticationRequiredError(AuthError):
    status_code = 401
    code = "AUTHENTICATION_REQUIRED"
    message = "로그인이 필요합니다."


class AccountDisabledError(AuthError):
    status_code = 403
    code = "ACCOUNT_DISABLED"
    message = "사용할 수 없는 계정입니다."


class ForbiddenError(AuthError):
    status_code = 403
    code = "FORBIDDEN"
    message = "접근 권한이 없습니다."


class SessionExpiredError(AuthError):
    status_code = 401
    code = "SESSION_EXPIRED"
    message = "세션이 만료되었습니다. 다시 로그인해 주세요."


class TooManyLoginAttemptsError(AuthError):
    status_code = 429
    code = "TOO_MANY_LOGIN_ATTEMPTS"
    message = "잠시 후 다시 시도해 주세요."


# ---------------------------------------------------------------------------
# 채팅 도메인 예외
# ---------------------------------------------------------------------------


class ChatError(Exception):
    """채팅 도메인 예외 베이스."""

    status_code: int = 500
    code: str = "CHAT_ERROR"
    message: str = "채팅 처리 중 오류가 발생했습니다."

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


class InvalidCursorError(ChatError):
    status_code = 422
    code = "INVALID_CURSOR"
    message = "페이지 조회 정보가 올바르지 않습니다."


class ChatSessionNotFoundError(ChatError):
    status_code = 404
    code = "CHAT_SESSION_NOT_FOUND"
    message = "채팅방을 찾을 수 없습니다."


class ChatStorageError(ChatError):
    status_code = 500
    code = "CHAT_STORAGE_ERROR"
    message = "채팅 데이터를 저장하는 중 오류가 발생했습니다."