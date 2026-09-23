# PYRO RENTALS — Gap Review and Fix Plan

The master prompt is strong on breadth. The following gaps were added as explicit engineering rules so the implementation remains safe under concurrency and real operations.

## Gaps fixed in this foundation

1. **Availability race between search and booking** — search is advisory only. Booking creation re-checks availability in a transaction and the database exclusion constraint is the final authority.
2. **Quote/payment race** — quotes are immutable, have an expiry, a pricing version and line items. A booking references the exact quote that was accepted.
3. **Mutation replay** — idempotency keys are persisted with request fingerprint and response reference. A repeated key with a different payload is rejected.
4. **Webhook replay/duplication** — provider event IDs are unique and webhook signatures are verified before state changes.
5. **Operator data isolation** — RBAC alone is insufficient. Queries are scoped by customer/operator ownership before returning records.
6. **Money correctness** — all amounts use `NUMERIC`/`Decimal`, explicit currency and separate line items. Floating point is prohibited.
7. **Auditability** — sensitive state transitions append audit records with actor, action, entity and request ID.
8. **Outbox boundary** — external notifications/payments must not be sent while a database transaction is half-finished. The architecture reserves a transactional outbox for reliable background delivery.
9. **Production provider safety** — sandbox adapters are development/test-only and startup validation rejects them in production.
10. **PII/secrets in logs** — structured logging rules require redaction of tokens, KYC payloads, payment secrets and signed URLs.

## Master-prompt areas that still need business/legal decisions

These are not silently guessed because they affect contracts, taxation, privacy or money movement:

- Exact KYC documents and verification provider by geography/service.
- Tax/GST invoicing, TCS/TDS and operator payout treatment.
- Cancellation percentages, grace periods and no-show rules.
- Security-deposit authorization vs capture behavior by gateway.
- Damage approval/dispute thresholds and who may approve deductions.
- Operator commission plans and payout cycles.
- Corporate credit limits and approval hierarchy.
- Data-retention periods for KYC, invoices, audit and support records.
- Refund SLA, settlement SLA, RPO/RTO and alert thresholds.

The implementation stores these as configuration/policy concepts rather than hardcoding business values.

## Remaining engineering gaps by phase

### Phase 2
- Full operator inventory CRUD and document expiry workflow.
- PostGIS pickup/service-area queries.
- Configurable pricing rules, holiday calendars and coupon stacking policy.
- Quote reservation/short hold policy for high-contention inventory.

### Phase 3
- Real Indian payment gateway adapter and reconciliation ingestion.
- KYC provider adapter and secure document quarantine/scanning pipeline.
- Deposit authorization/capture/refund ledger.
- Cancellation/refund engine.

### Phase 4
- Driver scheduling, handover, immutable inspection photos, damage disputes.
- Return charge computation and customer acknowledgement.

### Phase 5+
- Operator settlement ledger, finance approvals, reports, support, corporate, subscriptions, SEO, i18n and analytics.
- OpenTelemetry traces, SLO dashboards, load tests, restore drills and production runbooks.
