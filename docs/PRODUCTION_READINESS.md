# Production Readiness Gate

A feature is not complete because a page renders. For every production module verify database, API, validation, authentication, authorization, audit, errors, UI and tests.

## Gate

- [ ] All migrations apply on a clean PostgreSQL database.
- [ ] Authentication, refresh rotation and session invalidation tested.
- [ ] RBAC and ownership/IDOR tests pass.
- [ ] Concurrent conflicting booking test proves only one commit succeeds.
- [ ] Pricing and quote expiry/immutability tests pass.
- [ ] Payment webhook signature and duplicate-event tests pass.
- [ ] Refund/deposit/settlement ledger balances reconcile.
- [ ] KYC and file access use private storage + short-lived URLs.
- [ ] Rate limits and brute-force controls enabled.
- [ ] No production sandbox provider configured.
- [ ] PII redaction verified in logs/traces.
- [ ] Background jobs are retry-safe and outbox is monitored.
- [ ] Backups, PITR and restore drill documented and tested.
- [ ] CI lint/type/test/security/build stages are green.
- [ ] Performance/load targets and SLO alerts are defined and met.
- [ ] Accessibility and mobile responsive checks pass.
- [ ] Production secrets are in a secret manager, rotated and not in repo.
