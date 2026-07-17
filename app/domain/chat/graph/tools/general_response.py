"""
General Response Tool.

복지 정책과 관련 없는 질문(날씨, 일반 상식, 코딩 방법 등)을 처리한다.
"""

from langchain_core.tools import tool

OFF_TOPIC_MESSAGE = (
    "저는 복지 정책 안내 서비스입니다.\n"
    "복지 정책, 지원 대상, 신청 방법 등에 대해 질문해주세요."
)


@tool
def general_response_tool(query: str) -> str:
    """
    복지 정책과 관련 없는 질문일 때 사용한다.
    (예: 날씨, 일반 상식, 프로그래밍 방법 등)
    """
    return OFF_TOPIC_MESSAGE
