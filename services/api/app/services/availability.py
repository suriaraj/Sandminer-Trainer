from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, not_, select
from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus, Vehicle, VehicleBlock


RESERVING_BOOKING_STATUSES = {
    BookingStatus.QUOTE_CREATED,
    BookingStatus.PAYMENT_PENDING,
    BookingStatus.KYC_PENDING,
    BookingStatus.CONFIRMED,
    BookingStatus.READY_FOR_PICKUP,
    BookingStatus.VEHICLE_HANDED_OVER,
    BookingStatus.RENTAL_ACTIVE,
    BookingStatus.RETURN_PENDING,
    BookingStatus.VEHICLE_RETURNED,
    BookingStatus.INSPECTION_PENDING,
    BookingStatus.SETTLEMENT_PENDING,
    BookingStatus.DISPUTED,
}


def overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and start_b < end_a


def is_vehicle_available(db: Session, vehicle_id: UUID, pickup_at: datetime, return_at: datetime) -> bool:
    booking_conflict = db.scalar(
        select(
            exists().where(
                Booking.vehicle_id == vehicle_id,
                Booking.status.in_(RESERVING_BOOKING_STATUSES),
                Booking.pickup_at < return_at,
                Booking.return_at > pickup_at,
            )
        )
    )
    if booking_conflict:
        return False

    block_conflict = db.scalar(
        select(
            exists().where(
                VehicleBlock.vehicle_id == vehicle_id,
                VehicleBlock.start_at < return_at,
                VehicleBlock.end_at > pickup_at,
            )
        )
    )
    return not bool(block_conflict)


def search_available_vehicles(
    db: Session,
    city: str,
    pickup_at: datetime,
    return_at: datetime,
) -> list[Vehicle]:
    booking_conflict = exists().where(
        Booking.vehicle_id == Vehicle.id,
        Booking.status.in_(RESERVING_BOOKING_STATUSES),
        Booking.pickup_at < return_at,
        Booking.return_at > pickup_at,
    )
    block_conflict = exists().where(
        VehicleBlock.vehicle_id == Vehicle.id,
        VehicleBlock.start_at < return_at,
        VehicleBlock.end_at > pickup_at,
    )
    stmt = (
        select(Vehicle)
        .where(
            Vehicle.city.ilike(city),
            Vehicle.status == "AVAILABLE",
            not_(booking_conflict),
            not_(block_conflict),
        )
        .order_by(Vehicle.brand, Vehicle.model)
        .limit(100)
    )
    return list(db.scalars(stmt).all())
