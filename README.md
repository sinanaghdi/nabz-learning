# Nabz Learning

A Persian-first learning support platform for university courses.

The pilot is intentionally small: one instructor, one course, and a feedback loop that identifies learning topics that may need attention.

## Current phase

**Phase 5 — Learning analytics.** Instructors can review course-level results, student summaries, and topic accuracy from submitted attempts. These are API endpoints; dedicated Persian RTL dashboards are still a later phase.

## Technology

- Frontend: Next.js 16, React, TypeScript, Persian RTL
- Backend: FastAPI, Pydantic, SQLAlchemy 2
- Database: PostgreSQL; Alembic migrations
- Authentication: Argon2 password hashes and signed JWT bearer tokens
- Local development: Docker Compose
- CI: GitHub Actions

## Run locally

Requirements: Docker Desktop with Docker Compose.

1. Copy the environment template with Copy-Item .env.example .env in Windows PowerShell, or cp .env.example .env on macOS/Linux.
2. Start services with docker compose up --build.
3. Frontend: http://localhost:3000
4. API health: http://localhost:8000/api/v1/health
5. API docs: http://localhost:8000/docs

The backend container applies Alembic migrations on startup for local development. Use docker compose down to stop services. Add -v only when intentionally deleting the local PostgreSQL data volume.

## Create an instructor account

Public registration only creates student accounts. Run this command from a trusted terminal after the backend is running:

    docker compose exec backend python -m app.cli create-privileged-user --role instructor --email instructor@example.edu --full-name "Course Instructor"

The command prompts for the password twice without echoing it. Instructor/admin provisioning is not exposed as a public API.

## Main API routes

All routes use the /api/v1 prefix.

| Method | Route | Access |
|---|---|---|
| POST | /auth/register | Public; student only |
| POST | /auth/login | Public |
| GET | /auth/me | Authenticated |
| POST | /courses | Instructor/admin |
| POST | /courses/enroll | Student with join code |
| GET, POST | /courses/{id}/topics | Course access / manager |
| GET, POST | /courses/{id}/questions | Instructor/admin |
| POST | /courses/{id}/assessments | Course instructor/admin |
| GET | /courses/{id}/assessments | Instructor sees all; students see published only |
| POST | /courses/{id}/assessments/{id}/publish | Course instructor/admin |
| POST | /courses/{id}/assessments/{id}/attempts | Enrolled student |
| PUT | /attempts/{id}/answers/{question_id} | Attempt owner, active attempt only |
| POST | /attempts/{id}/submit | Attempt owner |
| GET | /courses/{id}/analytics/overview | Course instructor/admin |
| GET | /courses/{id}/analytics/topics | Course instructor/admin |
| GET | /courses/{id}/analytics/students | Course instructor/admin |

Topic accuracy counts each question in a submitted attempt as one presentation, including unanswered questions. The needs_review flag is a transparent heuristic: accuracy below 60% with at least three question presentations. It is an aid for the instructor, not an automated diagnosis of an individual learner. Topics with no observations return null accuracy rather than zero.

## Run checks

Backend (Python 3.12+):

    cd backend
    python -m pip install -e ".[dev]"
    ruff check app tests alembic
    alembic upgrade head --sql
    pytest

Frontend (Node.js 24 or compatible):

    cd frontend
    npm install
    npm run lint
    npm run typecheck
    npm run build

## Security boundary

The credentials in .env.example are local-only. Before real student data is used, the service needs managed secrets, TLS, backups, security review, rate limiting, account recovery/verification, an appropriate student-data privacy policy, and deployment controls. This scaffold is not production-ready.
