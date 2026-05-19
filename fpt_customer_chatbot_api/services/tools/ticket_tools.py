import uuid
from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
from sqlalchemy.orm import Session

# Import DB session and Models
try:
    from fpt_customer_chatbot_api.database import SessionLocal
    from fpt_customer_chatbot_api.models.ticket import Ticket, TicketStatus
    from fpt_customer_chatbot_api.models.user import User
except ImportError:
    from database import SessionLocal
    from models.ticket import Ticket, TicketStatus
    from models.user import User

# Global for testing override
_test_db: Optional[Session] = None

@tool
def create_support_ticket(content: str, description: str, user_id: str, email: str) -> str:
    """Create a support ticket in the database.
    Status transitions: None -> Pending.
    """
    db = _test_db or SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        uid = user.id if user else 1
        
        new_ticket = Ticket(
            ticket_id=str(uuid.uuid4()),
            content=content,
            description=description,
            user_id=uid,
            status=TicketStatus.Pending
        )
        db.add(new_ticket)
        db.commit()
        db.refresh(new_ticket)
        return f"Successfully created ticket {new_ticket.ticket_id}. Status: {new_ticket.status.value}"
    except Exception as e:
        return f"Error creating ticket: {str(e)}"
    finally:
        if _test_db is None:
            db.close()

@tool
def resolve_ticket(ticket_id: str, email: str) -> str:
    """Mark a support ticket as resolved.
    Status transitions: Pending/In Progress -> Resolved.
    """
    db = _test_db or SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            return f"No ticket found with ID {ticket_id}."
        
        ticket.status = TicketStatus.Resolved
        db.commit()
        return f"Ticket {ticket_id} has been marked as Resolved."
    finally:
        if _test_db is None:
            db.close()

@tool
def get_ticket_status(ticket_id: str, email: str) -> str:
    """Check the status of a support ticket."""
    db = _test_db or SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            return f"No ticket found with ID {ticket_id}."
        return f"Ticket {ticket_id} is currently {ticket.status.value}. Description: {ticket.description}"
    finally:
        if _test_db is None:
            db.close()

ticket_tools = [create_support_ticket, get_ticket_status, resolve_ticket]
