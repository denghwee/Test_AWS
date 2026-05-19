import uuid
from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    """Valid status transitions: Pending -> InProgress -> Resolved (or Canceled)"""
    PENDING = "Pending"
    IN_PROGRESS = "InProgress"
    RESOLVED = "Resolved"
    CANCELED = "Canceled"


class Ticket(BaseModel):
    """Full ticket data model for storage."""
    ticket_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    description: Optional[str] = None
    customer_name: str
    customer_phone: str
    email: Optional[str] = None
    status: TicketStatus = TicketStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)


# --- Tool Argument Schemas ---

class CreateTicket(BaseModel):
    """Schema for creating a new support ticket."""
    content: str = Field(description="Main request or issue of the ticket.")
    description: Optional[str] = Field(None, description="Detailed explanation of the issue.")
    customer_name: str = Field(description="Full name of the customer.")
    customer_phone: str = Field(description="Contact phone number of the customer.")
    email: Optional[str] = Field(None, description="Contact email address.")


class TrackTicket(BaseModel):
    """Schema for tracking/looking up a ticket by ID."""
    ticket_id: str = Field(description="The unique ID of the ticket to track.")


class UpdateTicket(BaseModel):
    """Schema for updating an existing ticket's fields."""
    ticket_id: str = Field(description="ID of the ticket to update.")
    content: Optional[str] = Field(None, description="Updated ticket content.")
    description: Optional[str] = Field(None, description="Updated description.")
    status: Optional[str] = Field(None, description="New status: Pending, InProgress, Resolved, Canceled.")


class CancelTicket(BaseModel):
    """Schema for canceling a ticket."""
    ticket_id: str = Field(description="ID of the ticket to cancel.")
