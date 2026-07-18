from app.domain.chat.graph.agent.states.credential_state import CredentialState
from app.domain.user.repository.repository import UserWelfareRepository
from app.infrastructure.db.connection import engine
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session


async def search_user_background(state: CredentialState) -> dict:
    """현재 사용자의 자격 판정용 상세 정보를 state에 적재한다."""
    user_id = state.get("user_id")
    if user_id is None:
        return {"user_background": None}

    def _find_user_background():
        with Session(engine) as session:
            return UserWelfareRepository(session).get_by_user_id(user_id)

    user_background = await run_in_threadpool(_find_user_background)
    return {"user_background": user_background}
