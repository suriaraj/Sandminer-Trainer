# PYRO RENTALS

Production-oriented vehicle rental and travel booking marketplace.

> PYRO RENTALS is an inventory-rental marketplace, not a ride-hailing clone. The core invariant is whether an exact vehicle can be rented for an exact period under an exact rental configuration.

## Repository layout

- `apps/web` — Next.js/React/TypeScript customer web application.
- `services/api` — FastAPI, SQLAlchemy, Alembic, business services and tests.
- `docs` — architecture, gap review, security, database, API, state-machine and readiness documentation.
- `.github/workflows/ci.yml` — API migration/test and web build CI.
- `docker-compose.yml` — PostgreSQL/PostGIS + Redis + API + worker + web.

## Implemented foundation

- JWT/password authentication foundation and server-side authorization helpers.
- PostgreSQL/PostGIS transactional schema.
- Exact-vehicle availability with active-booking and block checks.
- Database-level PostgreSQL exclusion constraint against overlapping reservations.
- Immutable quote records with expiry, pricing version and visible line items.
- Decimal/NUMERIC money handling with explicit currency.
- Booking state-machine validation and history.
- Idempotency persistence and replay protection.
- Audit-event foundation and transactional outbox table.
- Payment-provider interface with signed sandbox webhooks for development/test only.
- Production startup guard that rejects the sandbox payment provider.
- Health/readiness endpoints, request IDs and safe API errors.
- Mobile-first customer search page backed by the API.
- Docker, CI, migrations, tests and production-readiness documentation.

## Safety and correctness rules

No client response, frontend state, payment return URL, or search result is trusted as proof of availability, authorization or payment success. Those facts are revalidated server-side. Conflicting vehicle bookings are rejected by PostgreSQL even when requests race.

## Local development

1. Copy `.env.example` to `.env` and replace development secrets.
2. Run `docker compose up --build`.
3. Apply migrations with `docker compose run --rm api alembic upgrade head`.
4. API: `http://localhost:8000`; OpenAPI: `/docs`.
5. Web: `http://localhost:3000`.

## Validation

Backend unit tests cover price arithmetic, state transitions, overlap semantics and webhook signature verification. CI additionally applies the PostgreSQL migration before running the API tests and builds the Next.js application.

## Delivery status

This branch is a production-grade foundation and first vertical slice, not a false claim that every module in the master specification is already finished. `docs/GAP_REVIEW.md`, `docs/IMPLEMENTATION_ROADMAP.md` and `docs/PRODUCTION_READINESS.md` track what remains. A secure production super-admin bootstrap is intentionally not hardcoded into the repository.
