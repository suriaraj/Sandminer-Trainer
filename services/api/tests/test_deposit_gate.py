from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.deposits import deposit_cleared


class FakeSession:
    def __init__(self, deposit):
        self.deposit = deposit

    def scalar(self, statement):
        return self.deposit


def booking(amount):
    return SimpleNamespace(id=uuid4(), deposit_amount=Decimal(amount))


def test_zero_deposit_does_not_block_confirmation():
    assert deposit_cleared(FakeSession(None), booking("0"))


def test_outstanding_deposit_blocks_confirmation():
    assert not deposit_cleared(FakeSession(None), booking("5000"))
    assert not deposit_cleared(
        FakeSession(SimpleNamespace(status="PENDING")), booking("5000")
    )


def test_authorized_or_captured_deposit_allows_confirmation():
    for status in ("AUTHORIZED", "CAPTURED"):
        assert deposit_cleared(
            FakeSession(SimpleNamespace(status=status)), booking("5000")
        )
