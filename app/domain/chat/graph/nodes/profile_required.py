"""복지 추천에 필요한 사용자 정보가 없을 때 안내하는 노드."""
from app.domain.chat.graph.state2 import ChatState

PROFILE_REQUIRED_MESSAGE = (
    "맞춤 복지를 추천해드리려면 소득, 나이, 가구원 수 같은 기본 정보가 필요해요. "
    "마이페이지에서 정보를 입력해 주시면 다시 추천해드릴게요."
)


def profile_required(state: ChatState) -> dict:
    return {
        "answer": PROFILE_REQUIRED_MESSAGE,
        "intent": state.get("intent", "eligibility_agent"),
    }