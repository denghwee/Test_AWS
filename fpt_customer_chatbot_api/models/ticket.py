"""
Ticket Model
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


class TicketStatus(str, enum.Enum):
    Pending = "Pending"
    InProgress = "InProgress"
    Resolved = "Resolved"
    Canceled = "Canceled"


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticket_id = Column(
        String(36), unique=True, nullable=False, index=True,
        default=lambda: str(uuid.uuid4())
    )
    content = Column(String(1000), nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(
        SAEnum(TicketStatus, name="ticketstatus", create_type=True),
        default=TicketStatus.Pending,
        nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships
    user = relationship("User", back_populates="tickets")
