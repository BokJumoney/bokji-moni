"""구독 REST API 요청 DTO.

프런트가 보내는 JSON boolean만 허용하며 문자열 ``"true"``나 숫자 ``1``을
묵시적으로 boolean으로 바꾸지 않는다. 정의하지 않은 필드도 거부해 설정 API가
권한이나 내부 필드를 임의로 받지 않도록 한다.
"""

from pydantic import BaseModel, ConfigDict, StrictBool


class PolicyNewsUpdateRequest(BaseModel):
    """전체 정책 소식 수신 여부 변경 요청."""

    enabled: StrictBool

    model_config = ConfigDict(extra="forbid")