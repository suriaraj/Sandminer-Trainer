from decimal import Decimal

from sqlalchemy import select
from app.lifecycle_models import Deposit


def deposit_cleared(db, booking):
    if booking.deposit_amount <= Decimal(0):
        return True
    deposit = db.scalar(select(Deposit).where(Deposit.booking_id == booking.id))
    return bool(deposit and deposit.status in {'AUTHORIZED', 'CAPTURED'})
