from langchain_core.tools import tool
from app.rag.policy_retriever import search_policy_info

@tool
async def form_search_tool(query: str):
    """
    사용자가 언급한 정책의 신청서를 탐색 및 반환하는 tool
    언급된 정책이 없다면 -> 정책 없음을 반환
    정책은 있는데 신청서가 없다면 -> 신청서 없음을 반환
    """
    print("form_search_tool 실행")
    policy_docs = await search_policy_info(query=query, k=5)
    return policy_docs