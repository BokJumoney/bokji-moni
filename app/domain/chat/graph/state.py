from typing import List
from typing_extensions import TypedDict

class ChatGraphState(TypedDict):
    question: str
    generation: str
    documents: List[str]
    chat_history: List[dict]