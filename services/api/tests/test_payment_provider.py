import hashlib
import hmac

from app.providers.payment import SandboxPaymentProvider
from app.core.config import get_settings


def test_sandbox_webhook_signature():
    settings = get_settings()
    payload = b'{"event":"payment.pending"}'
    signature = hmac.new(settings.payment_secret.encode(), payload, hashlib.sha256).hexdigest()
    assert SandboxPaymentProvider().verify_webhook(payload, signature)
