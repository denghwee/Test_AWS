"""
Bookings Router - CRUD endpoints for room bookings
"""

from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_active_user
from ..models.user import User
from ..models.booking import BookingStatus
from ..schemas.booking import BookingCreate, BookingUpdate, BookingResponse
from ..crud import bookings as crud_bookings

router = APIRouter()


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_in: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new room booking.
    Validation: time must be in the future (already checked by Pydantic validator).
    """
    # Manual check just in case or if schema validator is not enough
    now = datetime.now(timezone.utc)
    target_time = booking_in.time
    if target_time.tzinfo is None:
        target_time = target_time.replace(tzinfo=timezone.utc)
    
    if target_time <= now:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking time must be in the future."
        )
    return crud_bookings.create_booking(db, booking_in, user_id=current_user.id)


@router.get("/", response_model=List[BookingResponse])
async def list_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[BookingStatus] = Query(None, alias="status"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List bookings with pagination and filters (status, date range)."""
    return crud_bookings.get_bookings(
        db, 
        user_id=current_user.id, 
        skip=skip, 
        limit=limit, 
        status=status_filter,
        date_from=date_from,
        date_to=date_to
    )


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific booking by its UUID booking_id."""
    booking = crud_bookings.get_booking_by_uuid(db, booking_id=booking_id, user_id=current_user.id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
    return booking


@router.put("/{booking_id}", response_model=BookingResponse)
async def update_booking(
    booking_id: str,
    booking_update: BookingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a booking.
    Validation: 
    - Only 'Scheduled' bookings can be updated.
    - New time must be in the future.
    """
    booking = crud_bookings.get_booking_by_uuid(db, booking_id=booking_id, user_id=current_user.id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

    if booking.status != BookingStatus.Scheduled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update a booking that is already {booking.status.value}."
        )

    if booking_update.time:
        now = datetime.now(timezone.utc)
        target_time = booking_update.time
        if target_time.tzinfo is None:
            target_time = target_time.replace(tzinfo=timezone.utc)
        if target_time <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New booking time must be in the future."
            )

    return crud_bookings.update_booking(db, db_obj=booking, obj_in=booking_update)


@router.delete("/{booking_id}", response_model=BookingResponse)
async def cancel_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Soft delete a booking by changing its status to 'Canceled'."""
    booking = crud_bookings.get_booking_by_uuid(db, booking_id=booking_id, user_id=current_user.id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
    
    if booking.status == BookingStatus.Canceled:
        raise HTTPException(status_code=400, detail="Booking is already canceled.")
        
    return crud_bookings.cancel_booking(db, db_obj=booking)
