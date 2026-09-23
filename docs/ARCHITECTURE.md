# System Architecture

## Shape

PYRO RENTALS starts as a modular monolith. It deliberately avoids premature microservices while preserving module boundaries that can later be extracted.

```text
Browser / future Flutter app
          |
          v
     Next.js Web
          |
          v
      FastAPI /api/v1
          |
  +-------+---------+------------------+
  |                 |                  |
PostgreSQL/PostGIS  Redis          Provider ports
  |                 |          payments/storage/maps/
  |                 |          notifications/KYC
  +------> Outbox -> Worker ------------+
```

## Core invariants

- The database, not the browser, prevents double booking.
- A quote is immutable once issued.
- Booking, payment, refund, deposit and settlement mutations are idempotent.
- Customer/operator ownership is enforced server-side in addition to RBAC.
- Payment success comes only from a verified provider event/reconciliation path.
- Financial balances are derived from immutable ledger entries, never arbitrary balance mutation.
- Sensitive documents are private objects reached through short-lived signed URLs.

## Module boundaries

`auth`, `users`, `operators`, `vehicles`, `availability`, `pricing`, `quotes`, `bookings`, `payments`, `deposits`, `handover`, `inspection`, `settlements`, `notifications`, `reports`, `audit`, `configuration`.

The initial code implements the cross-cutting core plus the critical search→quote→booking skeleton. Later modules must use the same transaction, authorization, audit and idempotency conventions.

## Booking concurrency

1. Search checks blocks and active bookings.
2. Client requests an immutable quote.
3. Booking request enters a transaction.
4. Server verifies quote owner, expiry, vehicle and dates.
5. Server inserts booking.
6. PostgreSQL exclusion constraint rejects any conflicting active booking even if two requests raced.
7. Commit succeeds for at most one conflicting booking.

## Reliability

Use request IDs, idempotency keys and transactional outbox records. Background jobs are retry-safe; provider calls carry deterministic external references. Consumers deduplicate by event ID.
