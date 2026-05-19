from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from ..models.ticket import Ticket, TicketStatus
from ..schemas.ticket import TicketCreate, TicketUpdate

def create_ticket(db: Session, ticket_in: TicketCreate, user_id: int) -> Ticket:
    db_obj = Ticket(
        ticket_id=str(uuid.uuid4()),
        content=ticket_in.content,
        description=ticket_in.description,
        user_id=user_id,
        status=TicketStatus.Pending
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_ticket_by_uuid(db: Session, ticket_id: str, user_id: int) -> Optional[Ticket]:
    return db.query(Ticket).filter(
        Ticket.ticket_id == ticket_id, 
        Ticket.user_id == user_id
    ).first()

def get_tickets(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[TicketStatus] = None
) -> List[Ticket]:
    query = db.query(Ticket).filter(Ticket.user_id == user_id)
    if status:
        query = query.filter(Ticket.status == status)
    return query.offset(skip).limit(limit).all()

def update_ticket(db: Session, db_obj: Ticket, obj_in: TicketUpdate) -> Ticket:
    update_data = obj_in.model_dump(exclude_unset=True)
    for field in update_data:
        setattr(db_obj, field, update_data[field])
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def cancel_ticket(db: Session, db_obj: Ticket) -> Ticket:
    db_obj.status = TicketStatus.Canceled
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
