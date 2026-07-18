"""
comming_soon.py
 
subscription_agent, eligibility_agent가 아직 구현되지 않았을 때
임시로 연결해두는 노드. intent_router가 이 두 카테고리로 분류한 질문은
전부 여기로 와서 "아직 준비 중" 안내를 answer로 채운다.
 
나중에 진짜 subscription_agent / eligibility_agent를 구현하면,
chat_graph.py에서 이 노드 대신 진짜 에이전트 노드로 매핑을 바꿔주면 된다.
"""
from app.domain.chat.graph.state2 import ChatState
 
_COMING_SOON_MESSAGE = (
    "죄송합니다, 해당 기능은 현재 준비 중입니다.\n"
    "복지 정책 정보(지원 대상, 신청 방법 등)는 지금 바로 안내해드릴 수 있어요."
)
 
 
async def comming_soon(state: ChatState) -> dict:
    return {"answer": _COMING_SOON_MESSAGE}
 