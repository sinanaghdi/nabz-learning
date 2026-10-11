# ADR 0001: Application Stack and Deployment Shape

- **Status:** Accepted for the pilot
- **Date:** 2026-10-11

## Context

Nabz Learning needs a maintainable foundation for a Persian-first web experience, a typed HTTP API, relational learning data, and a small pilot that can run locally with modest operational overhead. The product is still validating its assumptions.

## Decision

Use Next.js App Router, React, and TypeScript for the web app; FastAPI and Pydantic Settings for the API; SQLAlchemy 2 and PostgreSQL for persistence; Alembic for schema migrations; Docker Compose for local development; and GitHub Actions for checks. Keep a modular monolith and version API routes under `/api/v1`.

## Rationale

- Python and FastAPI align with the backend delivery plan.
- Next.js and TypeScript provide a component-based, typed UI.
- PostgreSQL supports constraints and transactions for course and assessment data.
- Compose makes the local environment reproducible without a hosted database.
- One backend deployment keeps a pilot easier to build, test, and operate.

## Consequences

**Benefits:** Clear frontend/API boundaries, conventional migrations, straightforward local startup, and room for domain modules to grow.

**Trade-offs:** Separate frontend/backend toolchains require maintenance. Authentication, authorization, privacy controls, observability, backups, and production hardening remain future work.

## Explicitly deferred

Redis, Celery, microservices, AI recommendations, payment infrastructure, public rankings, and job/research opportunity matching are not needed to validate the initial product loop.
