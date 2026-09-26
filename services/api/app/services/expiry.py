"""Release only unpaid, expired booking holds inside row-locked transactions."""
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.marketplace_models import VehicleReservation
from app.models import Booking, BookingStatus, OutboxEvent, Payment, PaymentStatus
from app.services.lifecycle import transition_booking


def release_expired_holds(db: Session, batch_size: int = 100) -> int:
    now = datetime.now(UTC)
    bookings = db.scalars(
        select(Booking)
        .where(
            Booking.status == BookingStatus.PAYMENT_PENDING,
            Booking.payment_deadline_at.is_not(None),
            Booking.payment_deadline_at < now,
        )
        .order_by(Booking.payment_deadline_at.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    ).all()
    expired = 0
    for booking in bookings:
        # A captured/authorized payment always requires reconciliation,
        # never silent release of paid inventory.
        paid = db.scalar(
            select(Payment.id).where(
                Payment.booking_id == booking.id,
                Payment.status.in_([PaymentStatus.CAPTURED, PaymentStatus.AUTHORIZED]),
            ).limit(1)
        )
        if paid is not None:
            db.add(OutboxEvent(
                id=uuid4(),
                topic="booking.paid_hold_reconciliation_required",
                aggregate_id=str(booking.id),
                payload={"booking_id": str(booking.id)},
                created_at=now,
            ))
            continue
        transition_booking(db, booking, BookingStatus.CANCELLED, None, "hold-expiry")
        reservation = db.scalar(select(VehicleReservation).where(
            VehicleReservation.booking_id == booking.id,
        ))
        if reservation is not None:
            reservation.status = "RELEASED"
        db.add(OutboxEvent(
            id=uuid4(),
            topic="booking.hold_expired",
            aggregate_id=str(booking.id),
            payload={"booking_id": str(booking.id)},
            created_at=now,
        ))
        expired += 1
    return expired
