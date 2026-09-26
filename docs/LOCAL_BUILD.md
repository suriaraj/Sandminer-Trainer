# PYRO RENTALS — local build and verification

This branch transforms the old Android starter tree into a web/API rental marketplace.
It does **not** produce an Android APK. The original Sandminer-Trainer code remains
unchanged on the repository's main branch until the draft PR is explicitly merged.
Use the feature branch for the new application.

## Prerequisites

Docker Engine with Docker Compose, enough disk space for PostgreSQL/PostGIS and
MinIO, and a modern browser. Java/Android SDK is not needed for PYRO RENTALS.

## Start

1. Copy the repository root `.env.example` to `.env`.
2. Replace the JWT and local object-storage development secrets. These are
   development-only values, not production credentials.
3. Run `docker compose up --build -d`.
4. Apply schema and permission migrations:

   ```sh
   docker compose exec api alembic upgrade head
   ```

5. Seed an explicitly fake development catalog (optional):

   ```sh
   docker compose exec api python -m app.dev_seed
   ```

6. Open the web application at localhost port 3000, API OpenAPI docs at port
   8000 under /docs, MinIO admin console at localhost port 9001 and API
   /ready for PostgreSQL/Redis readiness.

New customer accounts created via the web registration form receive a CUSTOMER
role. The fake seed creates 20 demonstrative operators, 100 demonstrative
vehicles across five cities and daily self-drive pricing packages. Never
treat those rates, vehicles or operator approvals as real inventory.

## Development administrator

Register a user through the web before granting the development admin role.
Then from an authorized local shell run:

```sh
docker compose exec api python -m app.admin_cli --email YOUR_REGISTERED_EMAIL --confirm
```

This command is intentionally refused in staging/production. Real production
administrator onboarding needs separate identity verification and an approved
audited operations procedure.

## Demonstrate a booking

1. Register and sign in at the web login screen.
2. Search a seeded city, choose SELF_DRIVE and exactly 24 hours or a multiple
   of its one-day package duration, using future pickup/return dates.
3. Select a vehicle and package. The server calculates immutable price
   components using Decimal and rechecks database availability.
4. Reserve the vehicle. Two concurrent claims for the same vehicle/time
   are resolved by PostgreSQL constraints. The unpaid hold expires after
   the configured booking-hold period and is then released by a scheduled
   worker.
5. See the new PAYMENT_PENDING booking in My Bookings. The sandbox payment
   adapter never claims real money was collected.
6. Initiate a sandbox payment using POST /api/v1/bookings/{booking_id}/payments
   and an Idempotency-Key header from OpenAPI. Sandbox gateway event simulation
   is development-only.
7. A signed simulated capture moves the booking to KYC_PENDING until an
   authorized reviewer approves service-specific KYC evidence.
8. In My KYC, submit the appropriate document using a direct signed private
   upload and confirm after upload. The reviewer verifies the document and
   records an expiry before final case approval.

The production payment processor, malware-scanning path, deposit capture,
regulated operator/vehicle document checks and full refund/settlement workflows
are not enabled. They must pass production gates before accepting actual rentals.

## Run tests

```sh
docker compose exec api pytest -q
docker compose exec api ruff check app tests
docker compose exec api alembic current
```

The GitHub Actions pipeline creates an isolated PostgreSQL/PostGIS + Redis test
environment, runs migrations, executes backend unit/integration tests including
concurrent same-vehicle booking, and builds the Next.js frontend. Review the
live workflow checks for the branch before merging.

## Failure isolation

- If /ready returns 503, check PostgreSQL, Redis and credentials first.
- If KYC presigned upload fails, check MinIO startup, storage credentials and
  the public storage hostname in .env.
- If a booking is rejected, check quote expiry, vehicle/operator status,
  configured service type, exact package duration and overlapping reservations.
- If money was captured but a hold expired, **do not** silently re-confirm the
  booking. The webhook records an outbox event for manual reconciliation.
- Back up database and private storage separately; a DB snapshot alone will
  not preserve KYC or inspection evidence.

## Deployment gate

The Docker Compose topology and sandbox gateway are for development, not an
approved public production deployment. Before launch complete the remaining
items in GAP_REVIEW.md and PRODUCTION_READINESS.md and verify legal/tax/privacy
requirements for each operating region.
