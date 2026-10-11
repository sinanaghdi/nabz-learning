# Nabz Learning

A Persian-first learning support platform for university courses.

The pilot is intentionally small: one instructor, one course, and a feedback loop that helps identify topic-level learning gaps.

## Current phase

**Phase 2 — Authentication and roles.** This repository now includes the API scaffold, a first users migration, student registration, email/password login, short-lived JWT access tokens, and server-side role checks. Quiz/course functionality is not implemented yet.

## Technology

- **Frontend:** Next.js 16, React, TypeScript, Persian RTL
- **Backend:** FastAPI, Pydantic, SQLAlchemy 2
- **Database:** PostgreSQL
- **Migrations:** Alembic
- **Password hashing:** Argon2 via pwdlib
- **Authentication:** Signed JWT bearer access tokens
- **Local environment:** Docker Compose
- **CI:** GitHub Actions

## Run locally

Requirements: Docker Desktop with Docker Compose.

1. Copy the environment template:
   - macOS/Linux: `cp .env.example .env`
   - Windows PowerShell: `Copy-Item .env.example .env`
2. Start the services: `docker compose up --build`
3. Frontend: [http://localhost:3000](http://localhost:3000)
4. Health endpoint: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
5. API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

The backend container runs `alembic upgrade head` on startup for local development. To stop the services, press `Ctrl+C`, then run `docker compose down`. Add `-v` only when you intend to delete local PostgreSQL data.

## Authentication API

All routes use the `/api/v1` prefix.

| Method | Route | Purpose |
|---|---|---|
| POST | `/auth/register` | Create a student account |
| POST | `/auth/login` | Exchange credentials for a bearer token |
| GET | `/auth/me` | Return the current authenticated account |
| GET | `/health` | Check that the API process responds |

Example registration body:

```json
{
  "email": "student@example.edu",
  "full_name": "Example Student",
  "password": "a-long-unique-password"
}
```

Registration always assigns the `student` role; additional role fields are rejected. Instructor and admin accounts must be provisioned through a trusted administrative workflow, which will be added in a later phase. For `/auth/me`, send the token from the login response in the `Authorization: Bearer <token>` header.

## Run checks

Backend checks (Python 3.12+):

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff check app tests alembic
pytest
```

Frontend checks (Node.js 24 LTS or another compatible supported release):

```bash
cd frontend
npm install
npm run lint
npm run typecheck
npm run build
```

## Project map

- `backend/app/api/`: API routes and authentication/authorization dependencies
- `backend/app/models/`: SQLAlchemy data models
- `backend/app/schemas/`: request and response validation
- `backend/alembic/versions/`: versioned database migrations
- `backend/tests/`: backend tests
- `frontend/`: Next.js application
- `docs/ARCHITECTURE.md`: system boundaries and data flow
- `docs/adr/`: architecture decisions

## Security boundaries

JWT secret and database credentials in the example configuration are local-only. Replace them with managed secrets before deployment. Production mode rejects the example JWT key. Passwords are never stored in plaintext or returned in API responses. Access tokens are short-lived; refresh tokens, email verification, password reset, rate limiting, account administration, and production security review are not yet implemented.

Do not use this scaffold to store real student data until those controls and the institution's privacy requirements have been reviewed.
