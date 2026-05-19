"""
Mock Store - In-Memory Storage

Provides in-memory dictionaries for ticket and booking data.
This allows the AI system to function independently without
database dependencies. Actual DB integration is in the FastAPI module.
"""

from typing import Optional


# ---------------------------------------------------------------------------
# In-memory storage
# ---------------------------------------------------------------------------
_ticket_store: dict[str, dict] = {}
_booking_store: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Ticket CRUD helpers
# ---------------------------------------------------------------------------

def store_ticket(ticket_id: str, data: dict) -> None:
    """Store a ticket in memory."""
    _ticket_store[ticket_id] = data


def get_ticket(ticket_id: str) -> Optional[dict]:
    """Retrieve a ticket by ID. Returns None if not found."""
    return _ticket_store.get(ticket_id)


def update_ticket_data(ticket_id: str, updates: dict) -> Optional[dict]:
    """Update specific fields of a ticket. Returns updated ticket or None."""
    ticket = _ticket_store.get(ticket_id)
    if ticket is None:
        return None
    for key, value in updates.items():
        if value is not None:
            ticket[key] = value
    _ticket_store[ticket_id] = ticket
    return ticket


def list_tickets() -> dict[str, dict]:
    """Return all tickets."""
    return dict(_ticket_store)


# ---------------------------------------------------------------------------
# Booking CRUD helpers
# ---------------------------------------------------------------------------

def store_booking(booking_id: str, data: dict) -> None:
    """Store a booking in memory."""
    _booking_store[booking_id] = data


def get_booking(booking_id: str) -> Optional[dict]:
    """Retrieve a booking by ID. Returns None if not found."""
    return _booking_store.get(booking_id)


def update_booking_data(booking_id: str, updates: dict) -> Optional[dict]:
    """Update specific fields of a booking. Returns updated booking or None."""
    booking = _booking_store.get(booking_id)
    if booking is None:
        return None
    for key, value in updates.items():
        if value is not None:
            booking[key] = value
    _booking_store[booking_id] = booking
    return booking


def list_bookings() -> dict[str, dict]:
    """Return all bookings."""
    return dict(_booking_store)
