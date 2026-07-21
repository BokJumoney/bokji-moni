"""구독 도메인의 안전한 외부 오류 계약."""


class SubscriptionError(Exception):
    """HTTP 상태·오류 코드·안전한 사용자 메시지를 가진 도메인 예외."""

    status_code = 500
    code = "SUBSCRIPTION_SERVICE_ERROR"
    message = "구독 정보를 처리하는 중 오류가 발생했습니다."

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


class PolicyNotFoundError(SubscriptionError):
    """구독 대상으로 사용할 정책을 식별할 수 없을 때 사용한다."""

    status_code = 404
    code = "POLICY_NOT_FOUND"
    message = "정책을 찾을 수 없습니다."


class SubscriptionStorageError(SubscriptionError):
    """DB 원문을 외부로 노출하지 않도록 저장소 오류를 정규화한다."""

    status_code = 500
    code = "SUBSCRIPTION_STORAGE_ERROR"
    message = "구독 정보를 저장하는 중 오류가 발생했습니다."
