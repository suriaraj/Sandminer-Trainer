from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


MONEY = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class PriceBreakdown:
    currency: str
    subtotal: Decimal
    tax: Decimal
    discount: Decimal
    deposit: Decimal
    total: Decimal
    line_items: dict


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def build_price(
    *,
    base_price: Decimal,
    deposit: Decimal,
    tax_rate: Decimal = Decimal("0"),
    discount: Decimal = Decimal("0"),
    currency: str = "INR",
) -> PriceBreakdown:
    if any(value < 0 for value in (base_price, deposit, tax_rate, discount)):
        raise ValueError("Pricing inputs cannot be negative")
    subtotal = money(base_price)
    tax = money(subtotal * tax_rate)
    applied_discount = min(money(discount), subtotal + tax)
    total = money(subtotal + tax - applied_discount)
    return PriceBreakdown(
        currency=currency,
        subtotal=subtotal,
        tax=tax,
        discount=applied_discount,
        deposit=money(deposit),
        total=total,
        line_items={
            "base_rental": str(subtotal),
            "tax": str(tax),
            "discount": str(applied_discount),
            "deposit": str(money(deposit)),
        },
    )
