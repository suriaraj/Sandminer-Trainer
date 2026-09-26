# Implementation status — PYRO RENTALS

This status distinguishes implemented and tested behavior from interfaces,
database-only scaffolding and features that still require integration or
policy approval. A passing build is NOT production approval.

## Implemented runtime flows

| Area | Current behavior | Gate |
| --- | --- | --- |
| Auth | Registration, password login, short-lived JWT, hashed refresh sessions, rotation, session revocation | Live smoke tests pass |
| RBAC | Seeded role/permission catalog, server-side checks, customer/operator query scoping | Extend IDOR/security suite |
| Customer search | Database vehicle/time/block lookup; future Flutter-compatible API | Expand service-area filtering |
| Pricing | Immutable expiring Decimal quote; service-scoped package and integer duration multiples | Dynamic fees/taxes policy pending |
| Booking | Idempotent creation, status-history records, row lock and two database exclusion constraints | Concurrency integration test |
| Unpaid hold expiry | Configurable deadline, scheduled Redis-backed Celery worker, reservation release | Expiry/reconciliation soak tests |
| Payment | Sandbox order initiation and HMAC-validated, deduplicated sandbox capture callbacks | Real Indian gateway missing |
| KYC | Service-specific case, private presigned S3-compatible upload, signature/hash checks and reviewer gate | Malware scan/retention/provider missing |
| Operator | Self-registration, tenant-scoped vehicle/package APIs, own booking lists, availability-policy API | Operator business verification pending |
| Admin | RBAC-controlled KPIs, operator/vehicle status APIs, KYC evidence-review APIs | Financial/admin approval flows incomplete |
| Rental fulfilment | Handover/return-inspection/damage record APIs with role and booking-state checks | Full evidence/charge/dispute chain pending |
| Support/reviews | Authenticated support-ticket creation and post-completion review APIs | Full moderation/support desk pending |
| Reliability | Request IDs, typed errors, audit foundation, Redis limits, outbox storage, readiness check | Outbox dispatcher, alerts/SLOs needed |
| Infra | Containerized frontend/API/PostGIS/Redis/Celery/MinIO development topology | Production infrastructure, DR pending |

## Database models without complete product workflows

Deposit ledger, double-entry-style accounting, settlement, damage approval,
notifications, inspection evidence and advanced KYC rules have storage or
partial service APIs; do not mistake model availability for operational
completeness. OpenAPI must be checked against the implementation in this
branch. No production payments or KYC claims should be made based on sandbox
or development data.

## Critical remaining release blockers

1. Replace sandbox payments with a verified real payment gateway, hosted
   checkout, refund/reconciliation handling and production webhook tests.
2. Require real operator and vehicle-document verification and expiry enforcement.
3. Integrate malware scanning, S3 retention policies, personal-data deletion
   procedures and legally reviewed KYC requirements before sensitive launch.
4. Implement deposit capture/release/charge dispute with immutable balanced
   ledger entries, approval controls and settlement reconciliation.
5. Complete driver dispatch, handover OTP/acknowledgement validation,
   photo evidence, return calculations and damage dispute workflow.
6. Implement transactional outbox delivery, notification retries,
   admin reports and finance payout approvals.
7. Complete accessibility and end-to-end browser tests, production hardening,
   deployment runbooks, monitoring, backup/restore drills and security review.
8. Close service-specific variable pricing (route/kilometre/toll/grace-period),
   corporate, subscriptions, travel packages and SEO expansion where needed.

## Demo safeguards

The development seed is intentionally fake; admin bootstrap is development/test
only; the production runtime rejects the sandbox gateway. Never activate
public rentals until the release blockers above are resolved and signed off.
