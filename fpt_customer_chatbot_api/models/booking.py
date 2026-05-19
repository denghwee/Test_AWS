"""
Booking Model
"""

import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
try:
    from ..database import Base
except ImportError:
    from database import Base  # type: ignore[no-redef]
import enum


class BookingStatus(str, enum.Enum):
    Scheduled = "Scheduled"
    Finished = "Finished"
    Canceled = "Canceled"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    booking_id = Column(
        String(36), unique=True, nullable=False, index=True,
        default=lambda: str(uuid.uuid4())
    )
    reason = Column(String(1000), nullable=False)
    time = Column(DateTime(timezone=True), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    note = Column(Text, nullable=True)
    status = Column(
        SAEnum(BookingStatus, name="bookingstatus", create_type=True),
        default=BookingStatus.Scheduled,
        nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships
    user = relationship("User", back_populates="bookings")
