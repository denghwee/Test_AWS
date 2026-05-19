import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
from sqlalchemy.orm import Session

try:
    from fpt_customer_chatbot_api.database import SessionLocal
    from fpt_customer_chatbot_api.models.booking import Booking, BookingStatus
    from fpt_customer_chatbot_api.models.user import User
except ImportError:
    from database import SessionLocal
    from models.booking import Booking, BookingStatus
    from models.user import User

# Global for testing override
_test_db: Optional[Session] = None

@tool
def create_room_booking(reason: str, time: str, email: str) -> str:
    """Create a room booking in the database. 'time' should be in ISO format.
    Status transitions: None -> Scheduled.
    """
    db = _test_db or SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        uid = user.id if user else 1
        
        try:
            booking_dt = datetime.fromisoformat(time.replace('Z', '+00:00'))
        except:
            return "Invalid time format. Please use ISO format (e.g. 2024-12-31T14:00:00)"

        new_booking = Booking(
            booking_id=str(uuid.uuid4()),
            reason=reason,
            time=booking_dt,
            user_id=uid,
            status=BookingStatus.Scheduled
        )
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)
        return f"Successfully booked room for {reason} at {time}. Booking ID: {new_booking.booking_id}. Status: {new_booking.status.value}"
    except Exception as e:
        return f"Error creating booking: {str(e)}"
    finally:
        if _test_db is None:
            db.close()

@tool
def update_booking_time(booking_id: str, new_time: str, email: str) -> str:
    """Update the time of an existing booking.
    Status transitions: Scheduled -> Scheduled (updated).
    """
    db = _test_db or SessionLocal()
    try:
        booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
        if not booking:
            return f"No booking found with ID {booking_id}."
        
        try:
            booking_dt = datetime.fromisoformat(new_time.replace('Z', '+00:00'))
        except:
            return "Invalid time format."

        booking.time = booking_dt
        db.commit()
        return f"Successfully updated booking {booking_id} to {new_time}."
    finally:
        if _test_db is None:
            db.close()

@tool
def cancel_room_booking(booking_id: str, email: str) -> str:
    """Cancel a room booking.
    Status transitions: Scheduled -> Cancelled.
    """
    db = _test_db or SessionLocal()
    try:
        booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
        if not booking:
            return f"No booking found with ID {booking_id}."
        
        booking.status = BookingStatus.Canceled
        db.commit()
        return f"Successfully cancelled booking {booking_id}. Status: {booking.status.value}"
    finally:
        if _test_db is None:
            db.close()

@tool
def list_user_bookings(email: str) -> str:
    """List all bookings for a user by email."""
    db = _test_db or SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return "User not found."
        
        bookings = db.query(Booking).filter(Booking.user_id == user.id).all()
        if not bookings:
            return "No bookings found for your account."
        
        res = "Your bookings:\n"
        for b in bookings:
            res += f"- {b.reason} at {b.time.isoformat()} (ID: {b.booking_id}, Status: {b.status.value})\n"
        return res
    finally:
        if _test_db is None:
            db.close()

booking_tools = [create_room_booking, update_booking_time, cancel_room_booking, list_user_bookings]
