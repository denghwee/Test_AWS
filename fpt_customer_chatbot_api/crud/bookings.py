from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
from ..models.booking import Booking, BookingStatus
from ..schemas.booking import BookingCreate, BookingUpdate

def create_booking(db: Session, booking_in: BookingCreate, user_id: int) -> Booking:
    db_obj = Booking(
        booking_id=str(uuid.uuid4()),
        reason=booking_in.reason,
        time=booking_in.time,
        note=booking_in.note,
        user_id=user_id,
        status=BookingStatus.Scheduled
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_booking_by_uuid(db: Session, booking_id: str, user_id: int) -> Optional[Booking]:
    return db.query(Booking).filter(
        Booking.booking_id == booking_id, 
        Booking.user_id == user_id
    ).first()

def get_bookings(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[BookingStatus] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> List[Booking]:
    query = db.query(Booking).filter(Booking.user_id == user_id)
    if status:
        query = query.filter(Booking.status == status)
    if date_from:
        query = query.filter(Booking.time >= date_from)
    if date_to:
        query = query.filter(Booking.time <= date_to)
    return query.offset(skip).limit(limit).all()

def update_booking(db: Session, db_obj: Booking, obj_in: BookingUpdate) -> Booking:
    update_data = obj_in.model_dump(exclude_unset=True)
    for field in update_data:
        setattr(db_obj, field, update_data[field])
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def cancel_booking(db: Session, db_obj: Booking) -> Booking:
    db_obj.status = BookingStatus.Canceled
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
