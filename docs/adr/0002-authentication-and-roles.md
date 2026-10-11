# ADR 0002: Initial Authentication and Role Policy

- **Status:** Accepted for the pilot
- **Date:** 2026-10-11

## Context

The first product increment needs identifiable student accounts and a reusable server-side way to enforce instructor/admin-only actions. Public users must not be able to grant themselves privileged roles.

## Decision

- Use normalized email plus password for the first sign-in mechanism.
- Hash passwords with Argon2 through pwdlib.
- Issue short-lived HS256 bearer JWTs with subject, issuer, issued-at, and expiry claims.
- Persist users in PostgreSQL through SQLAlchemy and Alembic.
- Start with `student`, `instructor`, and `admin` roles.
- Allow public registration to create student accounts only.
- Enforce role checks in backend dependencies, not in frontend visibility alone.
- Reject the example JWT signing key when `APP_ENV=production`.

## Consequences

The API gets a small, testable identity foundation without an external identity provider. The approach also means the project must implement or choose trusted account provisioning for instructors/admins before a wider pilot.

## Deferred

Email verification, password reset, refresh-token rotation, brute-force/rate limiting, SSO, MFA, recovery flows, admin user interface, and production threat modeling remain required before broad deployment. The current token design is a starter, not a claim of production readiness.
