# PYRO RENTALS

Production-oriented vehicle rental and travel booking marketplace.

> PYRO RENTALS is an inventory-rental marketplace, not a ride-hailing clone. The core invariant is whether an exact vehicle can be rented for an exact period under an exact rental configuration.

## Repository layout

- `apps/web` — Next.js/React/TypeScript customer web application.
- `services/api` — FastAPI application, SQLAlchemy models, Alembic migrations, business services and tests.
- `docs` — architecture, gap review, security, database, API, state-machine and readiness documentation.
- `.github/workflows/ci.yml` — lint/test/build/security-oriented CI foundation.
- `docker-compose.yml` — local PostgreSQL/PostGIS + Redis + API + web stack.

## Implemented foundation

The first production slice includes:

- JWT/password authentication foundation and RBAC permission checks.
- PostgreSQL/PostGIS data model for users, operators, vehicles, immutable quotes, bookings, payments, idempotency keys and audit events.
- Availability service that considers active bookings and vehicle blocks.
- Database-level exclusion constraint to reject overlapping bookings for the same vehicle.
- Immutable quote/pricing calculation using `Decimal`, with explicit currency and line items.
- Booking state-machine validation.
- Idempotency records for mutation replay protection.
- Payment-provider interface plus an explicit development-only sandbox adapter; production refuses the sandbox provider.
- Signed webhook verification contract and unique provider-event storage model.
- Health/readiness endpoints, request IDs and consistent API errors.
- Mobile-first customer search page wired to the API contract.
- Docker, CI, environment template, migration and documentation foundations.

## Important production rule

No client response, frontend state, or payment return URL is trusted as proof of availability, authorization or payment success. Those facts are verified server-side inside a database transaction or via verified provider webhooks.

## Local development

1. Copy `.env.example` to `.env` and replace all development secrets.
2. Run `docker compose up --build`.
3. API: `http://localhost:8000` and OpenAPI at `/docs`.
4. Web: `http://localhost:3000`.
5. Apply migrations in the API container with `alembic upgrade head`.

## Status

This branch is a production-grade **foundation and first vertical slice**, not a claim that every later module in the master requirements is fully finished. `docs/GAP_REVIEW.md` and `docs/IMPLEMENTATION_ROADMAP.md` explicitly track the remaining production work instead of returning fake success states.

## Development seed/admin commands

Inside the API container:

```bash
python -m app.cli seed-dev
python -m app.cli create-super-admin --email admin@example.test --password 'use-a-long-development-password'
```

The seed command uses clearly fake operators/vehicles. Never use it as production customer data.
