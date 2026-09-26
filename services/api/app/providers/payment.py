import hashlib
import hmac
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

from app.core.config import get_settings


@dataclass(frozen=True, slots=True)
class PaymentCheckout:
    provider: str
    external_reference: str
    status: str


class PaymentProvider:
    name: str

    def create_checkout(self, booking_id: UUID, amount: Decimal, currency: str) -> PaymentCheckout:
        raise NotImplementedError

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        raise NotImplementedError


class SandboxPaymentProvider(PaymentProvider):
    name = "sandbox"

    def create_checkout(self, booking_id: UUID, amount: Decimal, currency: str) -> PaymentCheckout:
        settings = get_settings()
        if settings.app_env == "production":
            raise RuntimeError("Sandbox payments are forbidden in production")
        return PaymentCheckout(
            provider=self.name,
            external_reference=f"sandbox-{booking_id}-{uuid4().hex[:12]}",
            status="PENDING",
        )

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        secret = get_settings().payment_secret.encode()
        expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


def payment_provider() -> PaymentProvider:
    settings = get_settings()
    if settings.payment_provider == "sandbox":
        return SandboxPaymentProvider()
    raise RuntimeError(f"Payment provider '{settings.payment_provider}' is not configured")
