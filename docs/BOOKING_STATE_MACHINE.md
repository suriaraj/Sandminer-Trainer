# Booking State Machine

Allowed lifecycle:

```text
DRAFT -> QUOTE_CREATED -> PAYMENT_PENDING -> KYC_PENDING -> CONFIRMED
CONFIRMED -> READY_FOR_PICKUP -> VEHICLE_HANDED_OVER -> RENTAL_ACTIVE
RENTAL_ACTIVE -> RETURN_PENDING -> VEHICLE_RETURNED -> INSPECTION_PENDING
INSPECTION_PENDING -> SETTLEMENT_PENDING -> COMPLETED
```

Terminal/side flows include `CANCELLED`, `REJECTED`, `NO_SHOW`, `DISPUTED`, `REFUND_PENDING`, `REFUNDED`.

Every transition must be authorized, validated, audited and idempotent. The service owns the transition map; callers cannot set an arbitrary status string.
