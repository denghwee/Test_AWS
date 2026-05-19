# models/__init__.py
# Import all models so that SQLAlchemy's Base.metadata is fully populated
# when create_all() is called from main.py or Alembic migrations.
#
# Uses try/except to support both:
#   - Package import: from .models import User  (FastAPI app)
#   - Direct import:  import models             (Alembic env.py)

try:
    from .user import User
    from .ticket import Ticket, TicketStatus
    from .booking import Booking, BookingStatus
    from .conversation import Conversation
except ImportError:
    from user import User               # type: ignore[no-redef]
    from ticket import Ticket, TicketStatus     # type: ignore[no-redef]
    from booking import Booking, BookingStatus  # type: ignore[no-redef]
    from conversation import Conversation       # type: ignore[no-redef]

__all__ = [
    "User",
    "Ticket", "TicketStatus",
    "Booking", "BookingStatus",
    "Conversation",
]
