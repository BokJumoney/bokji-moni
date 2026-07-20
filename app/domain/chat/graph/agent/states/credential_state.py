from typing import Annotated, TypedDict
from uuid import UUID

from langgraph.graph.message import add_messages

from app.domain.user.entity.models import UserWelfare


class CredentialState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    policy_name: str | None
    credential: str | None
    user_id: UUID
    user_background: UserWelfare | None
    error_message: str | None
    answer: str | None
