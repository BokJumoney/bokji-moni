# tools/welfare_recommendation.py
"""
맞춤 복지 추천 요청 여부를 LLM이 표시하기 위한 스키마.

실제로 tool_executor에서 실행되지 않는다. information_agent가
LLM 응답의 tool_calls에서 이 이름을 확인하고 직접 가로채서 처리한다.
"""
from pydantic import BaseModel, Field


class welfare_recommendation_tool(BaseModel):
    """사용자의 소득, 나이, 가구원 수 등 개인 정보를 바탕으로
    맞춤 복지를 추천할 때 선택합니다. '나에게 맞는', '내가 받을 수 있는',
    '정책 추천해줘' 같은 개인 맞춤 추천 요청일 때 사용하세요."""

    query: str = Field(description="사용자의 추천 요청 원문")