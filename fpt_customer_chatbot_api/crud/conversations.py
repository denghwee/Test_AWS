from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from ..models.conversation import Conversation
from ..schemas.chat import ConversationCreate

def create_conversation(db: Session, user_id: int) -> Conversation:
    db_obj = Conversation(
        conversation_id=str(uuid.uuid4()),
        user_id=user_id,
        title="New Chat"
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_conversation(db: Session, conversation_id: str, user_id: int) -> Optional[Conversation]:
    return db.query(Conversation).filter(
        Conversation.conversation_id == conversation_id,
        Conversation.user_id == user_id
    ).first()

def get_user_conversations(db: Session, user_id: int) -> List[Conversation]:
    return db.query(Conversation).filter(Conversation.user_id == user_id).all()

def update_conversation_title(db: Session, db_obj: Conversation, title: str) -> Conversation:
    db_obj.title = title
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
