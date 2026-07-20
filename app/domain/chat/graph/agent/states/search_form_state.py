from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class SearchFormState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    policy_name: str | None
    service_id: str | None
    forms: list[dict[str, str]]
    error_message: str | None
