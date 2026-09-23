# PYRO RENTALS — Gap Review and Fix Plan

The master prompt is strong on breadth. The implementation adds explicit engineering rules where concurrency, ownership, reliability and regulated data need stronger boundaries.

## Gaps fixed in this foundation

1. **Availability race between search and booking** — search is advisory only. Booking creation rechecks availability and the database exclusion constraint is the final authority.
2. **Quote/payment race** — quotes are immutable, have expiry, pricing version and line items. A booking references the accepted quote.
3. **Mutation replay** — idempotency keys persist request fingerprints and completed responses. Reusing a key with another payload is rejected.
4. **Concurrent idempotency-key use** — the unique database constraint prevents duplicate key ownership; concurrent duplicate work is rejected rather than creating two effects.
5. **Webhook replay** — provider event IDs are unique and webhook signatures must be verified before state changes.
6. **Operator/customer isolation** — permissions are not enough; resource queries must be scoped by ownership/tenant.
7. **Money correctness** — financial values use NUMERIC/Decimal with explicit currency and line items.
8. **Auditability** — sensitive transitions append audit events with actor, entity and request ID.
9. **Outbox boundary** — notification/provider work is separated from business transactions by a transactional outbox.
10. **Production-provider safety** — sandbox providers are development/test-only and are rejected in production.
11. **PII/secrets in telemetry** — tokens, KYC data, payment secrets and signed URLs must be redacted.

## Requirements that must remain configurable

These affect contracts, tax, privacy or financial liability and must not be guessed:

- KYC document requirements and verification provider by geography/service.
- Tax/GST invoicing and operator payout treatment.
- Cancellation percentages, grace periods and no-show policy.
- Security-deposit authorization/capture/refund behavior by gateway.
- Damage approval/dispute thresholds.
- Operator commission plans and payout cycles.
- Corporate credit limits and approval hierarchy.
- Retention periods for KYC, invoices, audit and support data.
- Refund/settlement SLAs and RPO/RTO.

## Remaining engineering work

### Inventory and availability
- Add explicit maintenance and operator-schedule entities rather than representing every closure as a generic block.
- Materialize configurable pickup/return buffer windows so the database exclusion rule protects buffers as well as the nominal rental interval.
- Add PostGIS service areas and pickup/drop geospatial queries.
- Add temporary reservation expiry cleanup for abandoned PAYMENT_PENDING bookings.

### Commerce
- Complete configurable rules pricing, weekend/holiday/demand rules and coupon policy.
- Implement real Indian payment gateway adapter, payment initiation, verified callbacks and reconciliation.
- Implement KYC provider integration and secure document quarantine/scanning.
- Implement deposit/refund/settlement ledgers with finance approval controls.

### Fulfilment and operations
- Driver scheduling, handover, immutable inspection evidence, damage disputes and return-charge computation.
- Operator/admin CRUD, reports, support, settlement operations, notifications and document expiry workflows.

### Hardening and expansion
- Refresh-token rotation and device/session revocation.
- Gateway/API rate limits and brute-force protection.
- OpenTelemetry traces, SLO dashboards, load tests, backup/restore drills and runbooks.
- Corporate rentals, subscriptions, travel packages, SEO, i18n and analytics.
