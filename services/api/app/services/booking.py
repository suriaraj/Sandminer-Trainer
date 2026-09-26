from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.core.config import get_settings
from app.models import Booking, BookingStatus, BookingStatusHistory, Quote, Vehicle
from app.marketplace_models import AvailabilityPolicy, RentalConfiguration, VehicleReservation
from app.services.availability import is_vehicle_available


ALLOWED_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.DRAFT: {BookingStatus.QUOTE_CREATED, BookingStatus.CANCELLED},
    BookingStatus.QUOTE_CREATED: {BookingStatus.PAYMENT_PENDING, BookingStatus.CANCELLED},
    BookingStatus.PAYMENT_PENDING: {
        BookingStatus.KYC_PENDING, BookingStatus.CONFIRMED, BookingStatus.CANCELLED
    },
    BookingStatus.KYC_PENDING: {
        BookingStatus.CONFIRMED, BookingStatus.REJECTED, BookingStatus.CANCELLED
    },
    BookingStatus.CONFIRMED: {
        BookingStatus.READY_FOR_PICKUP, BookingStatus.CANCELLED, BookingStatus.NO_SHOW
    },
    BookingStatus.READY_FOR_PICKUP: {
        BookingStatus.VEHICLE_HANDED_OVER, BookingStatus.CANCELLED, BookingStatus.NO_SHOW
    },
    BookingStatus.VEHICLE_HANDED_OVER: {BookingStatus.RENTAL_ACTIVE},
    BookingStatus.RENTAL_ACTIVE: {BookingStatus.RETURN_PENDING, BookingStatus.DISPUTED},
    BookingStatus.RETURN_PENDING: {BookingStatus.VEHICLE_RETURNED, BookingStatus.DISPUTED},
    BookingStatus.VEHICLE_RETURNED: {BookingStatus.INSPECTION_PENDING},
    BookingStatus.INSPECTION_PENDING: {
        BookingStatus.SETTLEMENT_PENDING, BookingStatus.DISPUTED
    },
    BookingStatus.SETTLEMENT_PENDING: {
        BookingStatus.COMPLETED, BookingStatus.REFUND_PENDING, BookingStatus.DISPUTED
    },
    BookingStatus.REFUND_PENDING: {BookingStatus.REFUNDED, BookingStatus.DISPUTED},
    BookingStatus.REFUNDED: {BookingStatus.COMPLETED},
    BookingStatus.DISPUTED: {
        BookingStatus.SETTLEMENT_PENDING, BookingStatus.REFUND_PENDING, BookingStatus.COMPLETED
    },
}


def assert_transition(current: BookingStatus, target: BookingStatus) -> None:
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ConflictError(
            "INVALID_BOOKING_TRANSITION",
            f"Cannot transition {current.value} to {target.value}",
        )


def _booking_number(now: datetime, booking_id: UUID) -> str:
    return f"PYRO-{now.year}-{str(booking_id).replace('-', '')[:6].upper()}"


def create_booking_from_quote(db: Session, quote: Quote, customer_id: UUID) -> Booking:
    now = datetime.now(UTC)
    if quote.customer_id != customer_id:
        raise ConflictError("QUOTE_OWNER_MISMATCH", "Quote does not belong to this customer")
    if quote.expires_at <= now:
        raise ConflictError("QUOTE_EXPIRED", "The quote has expired")
    # Serialize competing writes on the exact inventory item before checking availability.
    vehicle = db.get(Vehicle, quote.vehicle_id, with_for_update=True)
    if vehicle is None or vehicle.status != "AVAILABLE":
        raise ConflictError("VEHICLE_NOT_AVAILABLE", "Vehicle is not available")
    if not is_vehicle_available(db, quote.vehicle_id, quote.pickup_at, quote.return_at):
        raise ConflictError("VEHICLE_NOT_AVAILABLE", "The selected vehicle is no longer available")

    rental_config = db.scalar(
        select(RentalConfiguration).where(RentalConfiguration.quote_id == quote.id)
    )
    if rental_config is None:
        raise ConflictError(
            "RENTAL_CONFIGURATION_MISSING",
            "Quote rental configuration is missing",
        )

    policy = db.scalar(
        select(AvailabilityPolicy).where(
            AvailabilityPolicy.operator_id == vehicle.operator_id
        )
    )
    if policy is None:
        policy = db.scalar(
            select(AvailabilityPolicy).where(AvailabilityPolicy.scope_key == "GLOBAL")
        )
    if policy is None:
        raise ConflictError(
            "AVAILABILITY_POLICY_MISSING",
            "Availability buffer policy is not configured",
        )

    booking_id = uuid4()
    deadline = now + timedelta(minutes=get_settings().booking_hold_minutes)
    booking = Booking(
        id=booking_id,
        booking_number=_booking_number(now, booking_id),
        customer_id=customer_id,
        operator_id=vehicle.operator_id,
        vehicle_id=quote.vehicle_id,
        quote_id=quote.id,
        pickup_at=quote.pickup_at,
        return_at=quote.return_at,
        status=BookingStatus.PAYMENT_PENDING,
        payment_deadline_at=deadline,
        currency=quote.currency,
        total_amount=quote.total,
        deposit_amount=quote.deposit,
        created_at=now,
        updated_at=now,
    )
    db.add(booking)
    try:
        db.flush()
    except IntegrityError as exc:
        raise ConflictError(
            "VEHICLE_NOT_AVAILABLE",
            "The selected vehicle was reserved by another booking",
        ) from exc
    rental_config.booking_id = booking.id
    db.add(
        VehicleReservation(
            id=uuid4(),
            booking_id=booking.id,
            vehicle_id=booking.vehicle_id,
            start_at=booking.pickup_at - timedelta(minutes=policy.pre_buffer_minutes),
            end_at=booking.return_at + timedelta(minutes=policy.post_buffer_minutes),
            status="ACTIVE",
            expires_at=deadline,
            created_at=now,
        )
    )
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            from_status=BookingStatus.QUOTE_CREATED.value,
            to_status=BookingStatus.PAYMENT_PENDING.value,
            actor_user_id=customer_id,
            created_at=now,
        )
    )
    try:
        db.flush()
    except IntegrityError as exc:
        raise ConflictError(
            "VEHICLE_NOT_AVAILABLE",
            "The selected vehicle was reserved by another booking",
        ) from exc
    return booking
