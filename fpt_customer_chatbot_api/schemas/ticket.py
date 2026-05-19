"""
Ticket Schemas - Pydantic models for request/response validation
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from ..models.ticket import TicketStatus


# ── Request Schemas ─────────────────────────────────────────────────────────

class TicketCreate(BaseModel):
    content: str
    description: Optional[str] = None


class TicketUpdate(BaseModel):
    content: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TicketStatus] = None


# ── Response Schemas ─────────────────────────────────────────────────────────

class TicketResponse(BaseModel):
    id: int
    ticket_id: str
    content: str
    description: Optional[str] = None
    user_id: int
    status: TicketStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
