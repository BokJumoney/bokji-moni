"""
사용자 배경 정보 완성도를 확인하는 가드.

"추천 요청인지 아닌지" 판단은 information_agent의 LLM이
tool_calls로 직접 결정한다(welfare_recommendation_tool 선택 여부).
여기는 배경정보가 충분한지만 판단한다.
"""
from typing import Optional

REQUIRED_BACKGROUND_FIELDS = ("income", "age", "family_size")

PROFILE_REQUIRED_MESSAGE = (
    "맞춤 복지를 추천해드리려면 소득, 나이, 가구원 수 같은 기본 정보가 필요해요. "
    "마이페이지에서 정보를 입력해 주시면 다시 추천해드릴게요."
)


def is_background_complete(background: Optional[dict]) -> bool:
    if not background:
        return False
    return all(background.get(field) is not None for field in REQUIRED_BACKGROUND_FIELDS)