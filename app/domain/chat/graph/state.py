from typing import List
from typing_extensions import TypedDict

from langchain_core.documents import Document


class ChatGraphState(TypedDict):
    question: str
    generation: str
    documents: List[Document]
    chat_history: List[dict]