from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class ChatMessageResponse(BaseModel):
    response: str
    session_id: str
    intent: str = ""
    user_info_updated: bool = False
    needs_followup: bool = False
    sources: Optional[List[Dict]] = None

class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime
    intent: Optional[str] = None

class SessionSummary(BaseModel):
    session_id: str
    title: str
    last_message_at: datetime
    message_count: int