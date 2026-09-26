from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AuthorizationError, ConflictError, NotFoundError
from app.lifecycle_models import LedgerEntry, LedgerTransaction
from app.marketplace_models import VehicleReservation
from app.models import Booking, BookingStatus, BookingStatusHistory, OperatorUser, User
from app.services.booking import assert_transition


def get_customer_booking(db: Session, booking_id: UUID, customer_id: UUID) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None or booking.customer_id != customer_id:
        raise NotFoundError("Booking not found")
    return booking


def get_operator_booking(db: Session, booking_id: UUID, user: User) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise NotFoundError("Booking not found")
    owns_operator = db.scalar(
        select(func.count())
        .select_from(OperatorUser)
        .where(
            OperatorUser.user_id == user.id,
            OperatorUser.operator_id == booking.operator_id,
        )
    )
    if not owns_operator:
        raise AuthorizationError("Booking does not belong to your operator")
    return booking


def transition_booking(
    db: Session,
    booking: Booking,
    target: BookingStatus,
    actor_user_id: UUID | None,
    request_id: str | None,
) -> None:
    current = booking.status
    assert_transition(current, target)
    booking.status = target
    booking.updated_at = datetime.now(UTC)
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            from_status=current.value,
            to_status=target.value,
            actor_user_id=actor_user_id,
            request_id=request_id,
            created_at=datetime.now(UTC),
        )
    )
    if target in {
        BookingStatus.CANCELLED,
        BookingStatus.REJECTED,
        BookingStatus.NO_SHOW,
        BookingStatus.COMPLETED,
        BookingStatus.REFUNDED,
    }:
        reservation = db.scalar(
            select(VehicleReservation).where(
                VehicleReservation.booking_id == booking.id
            )
        )
        if reservation is not None:
            reservation.status = "RELEASED"


def write_balanced_ledger(
    db: Session,
    *,
    reference_type: str,
    reference_id: str,
    currency: str,
    description: str,
    entries: list[tuple[str, str, Decimal]],
) -> UUID:
    debit = sum((amount for _, direction, amount in entries if direction == "DEBIT"), Decimal("0"))
    credit = sum((amount for _, direction, amount in entries if direction == "CREDIT"), Decimal("0"))
    if debit != credit:
        raise ConflictError("UNBALANCED_LEDGER", "Ledger transaction must balance")
    if debit < 0 or credit < 0:
        raise ConflictError("INVALID_LEDGER_AMOUNT", "Ledger amounts cannot be negative")

    now = datetime.now(UTC)
    transaction_id = uuid4()
    db.add(
        LedgerTransaction(
            id=transaction_id,
            reference_type=reference_type,
            reference_id=reference_id,
            currency=currency,
            description=description,
            created_at=now,
        )
    )
    for account_code, direction, amount in entries:
        if direction not in {"DEBIT", "CREDIT"}:
            raise ConflictError("INVALID_LEDGER_DIRECTION", "Ledger direction is invalid")
        db.add(
            LedgerEntry(
                id=uuid4(),
                transaction_id=transaction_id,
                account_code=account_code,
                direction=direction,
                amount=amount,
                created_at=now,
            )
        )
    return transaction_id
