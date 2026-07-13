from pydantic import BaseModel
from typing import Optional

class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None