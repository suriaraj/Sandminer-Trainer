# Database Design

PostgreSQL/PostGIS is authoritative for transactional state. UUIDs are used for externally visible primary keys. Timestamps are UTC (`TIMESTAMPTZ`). Money uses `NUMERIC(14,2)` and an ISO currency column.

## Initial tables

- `users`, `roles`, `permissions`, `user_roles`, `role_permissions`
- `operators`, `operator_users`
- `vehicle_categories`, `vehicles`, `vehicle_blocks`
- `pricing_packages`, `quotes`, `quote_items`
- `bookings`, `booking_status_history`
- `payments`, `payment_events`
- `idempotency_keys`
- `audit_logs`
- `outbox_events`

## Critical constraints

`bookings` has a PostgreSQL `EXCLUDE USING gist` constraint over:

- `vehicle_id WITH =`
- `tstzrange(pickup_at, return_at, '[)') WITH &&`

for statuses that reserve inventory. This makes double booking a database error rather than a timing-dependent application behavior.

`payment_events(provider, provider_event_id)` and `idempotency_keys(scope, key)` are unique.

## Expansion

Later migrations add KYC/document, deposit ledger, wallet ledger, refund, handover, inspection/damage, driver, settlement, corporate, support, review, coupon/referral, analytics and notification tables without weakening the initial invariants.
