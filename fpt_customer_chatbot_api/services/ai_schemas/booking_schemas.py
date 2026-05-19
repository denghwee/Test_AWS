import uuid
from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class BookingStatus(str, Enum):
    """Valid status transitions: Scheduled -> Finished (or Canceled)"""
    SCHEDULED = "Scheduled"
    FINISHED = "Finished"
    CANCELED = "Canceled"


class Booking(BaseModel):
    """Full booking data model for storage."""
    booking_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reason: str
    time: datetime
    customer_name: str
    customer_phone: str
    email: Optional[str] = None
    note: Optional[str] = None
    status: BookingStatus = BookingStatus.SCHEDULED
    created_at: datetime = Field(default_factory=datetime.now)


# --- Tool Argument Schemas ---

class BookRoom(BaseModel):
    """Schema for creating a new room booking."""
    reason: str = Field(description="Reason for booking the room.")
    time: str = Field(description="Date and time of the booking (ISO format, must be in the future). Example: 2026-04-17T14:00:00")
    customer_name: str = Field(description="Full name of the customer.")
    customer_phone: str = Field(description="Contact phone number.")
    email: Optional[str] = Field(None, description="Contact email address.")
    note: Optional[str] = Field(None, description="Additional notes for the booking.")


class TrackBooking(BaseModel):
    """Schema for tracking/looking up a booking by ID."""
    booking_id: str = Field(description="The unique ID of the booking to track.")


class UpdateBooking(BaseModel):
    """Schema for updating an existing booking."""
    booking_id: str = Field(description="ID of the booking to update.")
    reason: Optional[str] = Field(None, description="Updated reason.")
    time: Optional[str] = Field(None, description="Updated date/time (ISO format, must be future).")
    note: Optional[str] = Field(None, description="Updated notes.")


class CancelBooking(BaseModel):
    """Schema for canceling a booking."""
    booking_id: str = Field(description="ID of the booking to cancel.")
