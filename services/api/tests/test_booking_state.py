import pytest

from app.core.errors import ConflictError
from app.models import BookingStatus
from app.services.booking import assert_transition


def test_valid_booking_transition():
    assert_transition(BookingStatus.CONFIRMED, BookingStatus.READY_FOR_PICKUP)


def test_invalid_booking_transition_is_rejected():
    with pytest.raises(ConflictError):
        assert_transition(BookingStatus.CONFIRMED, BookingStatus.COMPLETED)
