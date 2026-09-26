from decimal import Decimal

from app.services.pricing import build_price


def test_price_uses_decimal_and_visible_components():
    result = build_price(
        base_price=Decimal("1000.00"),
        deposit=Decimal("5000.00"),
        tax_rate=Decimal("0.18"),
        discount=Decimal("100.00"),
    )
    assert result.subtotal == Decimal("1000.00")
    assert result.tax == Decimal("180.00")
    assert result.discount == Decimal("100.00")
    assert result.total == Decimal("1080.00")
    assert result.deposit == Decimal("5000.00")
