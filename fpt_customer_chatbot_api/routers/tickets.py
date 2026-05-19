"""
Tickets Router - CRUD endpoints for support tickets
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_active_user
from ..models.user import User
from ..models.ticket import TicketStatus
from ..schemas.ticket import TicketCreate, TicketUpdate, TicketResponse
from ..crud import tickets as crud_tickets

router = APIRouter()


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_in: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new support ticket."""
    return crud_tickets.create_ticket(db, ticket_in, user_id=current_user.id)


@router.get("/", response_model=List[TicketResponse])
async def list_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[TicketStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all tickets belonging to the authenticated user with optional status filter."""
    return crud_tickets.get_tickets(
        db, user_id=current_user.id, skip=skip, limit=limit, status=status_filter
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific ticket by its UUID ticket_id."""
    ticket = crud_tickets.get_ticket_by_uuid(db, ticket_id=ticket_id, user_id=current_user.id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    return ticket


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    ticket_update: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a ticket's status. 
    Validation: Restricted to status transitions only according to business rules.
    """
    ticket = crud_tickets.get_ticket_by_uuid(db, ticket_id=ticket_id, user_id=current_user.id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")

    # Business Rule: If updating status, check transitions
    if ticket_update.status:
        current_status = ticket.status
        new_status = ticket_update.status

        # Rule 1: Cannot update a Resolved or Canceled ticket
        if current_status in [TicketStatus.Resolved, TicketStatus.Canceled]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update a ticket that is already {current_status.value}."
            )
        
        # Rule 2: Normal flow is Pending -> InProgress -> Resolved
        # But we allow canceling from Pending or InProgress.
        
    return crud_tickets.update_ticket(db, db_obj=ticket, obj_in=ticket_update)


@router.delete("/{ticket_id}", response_model=TicketResponse)
async def cancel_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Soft delete a ticket by changing its status to 'Canceled'."""
    ticket = crud_tickets.get_ticket_by_uuid(db, ticket_id=ticket_id, user_id=current_user.id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    
    if ticket.status == TicketStatus.Canceled:
        raise HTTPException(status_code=400, detail="Ticket is already canceled.")
        
    return crud_tickets.cancel_ticket(db, db_obj=ticket)
