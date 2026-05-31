import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..dependencies import get_current_active_user
from ..models.user import User
from ..schemas.chat import (
    MessageCreate, ChatResponse, ConfirmRequest, 
    ConversationCreate, ConversationResponse, ConversationHistoryResponse
)
from ..crud import conversations as crud_conversations
from ..services.ai_adapter import ai_adapter

router = APIRouter()


def _stream_event(event: str, data: dict) -> str:
    return json.dumps({"event": event, "data": data}, ensure_ascii=False) + "\n"

@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def start_conversation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Start a new AI chatbot conversation session."""
    return crud_conversations.create_conversation(db, user_id=current_user.id)

@router.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(
    conversation_id: str,
    message_in: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send a message to the AI and get a response."""
    # Verify conversation ownership
    conv = crud_conversations.get_conversation(db, conversation_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.title in (None, "", "New Chat", "New Conversation"):
        title = message_in.content.strip().replace("\n", " ")[:60]
        if title:
            crud_conversations.update_conversation_title(db, conv, title)
    
    user_info = {"user_id": current_user.id, "email": current_user.email}
    return await ai_adapter.process_message(
        message_in.content, 
        conversation_id, 
        user_info=user_info
    )


@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: str,
    message_in: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send a message and stream the assistant response as NDJSON events."""
    conv = crud_conversations.get_conversation(db, conversation_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.title in (None, "", "New Chat", "New Conversation"):
        title = message_in.content.strip().replace("\n", " ")[:60]
        if title:
            crud_conversations.update_conversation_title(db, conv, title)

    user_info = {"user_id": current_user.id, "email": current_user.email}

    async def event_generator():
        async for event in ai_adapter.stream_message(
            message_in.content,
            conversation_id,
            user_info=user_info
        ):
            yield _stream_event(event["event"], event.get("data", {}))

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache"}
    )

@router.post("/conversations/{conversation_id}/confirm", response_model=ChatResponse)
async def confirm_action(
    conversation_id: str,
    confirm_in: ConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Confirm or cancel a pending sensitive action (HITL)."""
    conv = crud_conversations.get_conversation(db, conversation_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return await ai_adapter.confirm_action(conversation_id, confirm_in.confirm)


@router.post("/conversations/{conversation_id}/confirm/stream")
async def stream_confirm_action(
    conversation_id: str,
    confirm_in: ConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Confirm or cancel a pending action and stream the assistant response."""
    conv = crud_conversations.get_conversation(db, conversation_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    async def event_generator():
        async for event in ai_adapter.stream_confirm_action(
            conversation_id,
            confirm_in.confirm
        ):
            yield _stream_event(event["event"], event.get("data", {}))

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache"}
    )

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all conversation sessions for the current user."""
    return crud_conversations.get_user_conversations(db, user_id=current_user.id)


@router.get("/conversations/{conversation_id}/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Return public chat history for a conversation session."""
    conv = crud_conversations.get_conversation(db, conversation_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ai_adapter.get_conversation_history(conversation_id)
