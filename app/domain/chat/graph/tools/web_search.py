"""
Web Search Tool.

최신 정책 변경, 올해 신규 정책, 신청 기간 변경 등 벡터DB에 없거나
최신성이 필요한 정보를 웹 검색으로 보완한다.

Tavily API를 사용한다. TAVILY_API_KEY는 os.environ에서 암묵적으로
읽히게 두지 않고, settings.tavily_api_key로 명시적으로 전달한다
(openai_api_key, database_url과 같은 패턴).

config.py의 Settings 클래스에 아래 필드가 없다면 추가해야 한다:
    tavily_api_key: str
(.env 파일에는 TAVILY_API_KEY=tvly-... 한 줄 추가)
"""

from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults

from app.infrastructure.config import settings

_tavily = TavilySearchResults(
    max_results=3,
    tavily_api_key=settings.TAVILY_API_KEY,
    include_domains=[
        "bokjiro.go.kr",
        "mohw.go.kr",
        "gov.kr",
        "easylaw.go.kr",
    ],
)


@tool
async def web_search_tool(query: str) -> str:
    """
    최신 정책 변경 사항, 올해 신규 정책, 신청 기간 변경 여부 등
    최신성이 필요하거나 policy_search_tool 결과만으로 정보가
    부족할 때 사용한다.
    """
    results = await _tavily.ainvoke({"query": query})

    if not results:
        return "웹 검색 결과를 찾지 못했습니다."

    return "\n\n".join(
        f"- {r.get('title', '')}: {r.get('content', '')} ({r.get('url', '')})"
        for r in results
    )
