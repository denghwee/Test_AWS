"""
Booking Schemas - Pydantic models for request/response validation
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from ..models.booking import BookingStatus


# ── Request Schemas ─────────────────────────────────────────────────────────

class BookingCreate(BaseModel):
    reason: str
    time: datetime
    note: Optional[str] = None


class BookingUpdate(BaseModel):
    reason: Optional[str] = None
    time: Optional[datetime] = None
    note: Optional[str] = None
    status: Optional[BookingStatus] = None


# ── Response Schemas ─────────────────────────────────────────────────────────

class BookingResponse(BaseModel):
    id: int
    booking_id: str
    reason: str
    time: datetime
    user_id: int
    note: Optional[str] = None
    status: BookingStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
