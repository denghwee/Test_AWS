from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class MessageCreate(BaseModel):
    content: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: List[ChatMessage]
    status: str = "success"
    tool_calls: Optional[List[Any]] = None

class ChatResponse(BaseModel):
    response: str
    status: str
    tool_calls: Optional[List[Any]] = None

class ConfirmRequest(BaseModel):
    confirm: bool

class ConversationCreate(BaseModel):
    pass

class ConversationResponse(BaseModel):
    conversation_id: str
    title: str
    created_at: datetime

    class Config:
        from_attributes = True
