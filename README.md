# Nabz Learning

A Persian-first learning support platform for university courses.

The pilot is intentionally small: one instructor, one course, and a feedback loop that helps identify topic-level learning gaps.

## Current phase

**Phase 3 — Courses and question bank.** The repository includes student registration/login, course creation, join-code enrollment, instructor-owned topics, and a single-choice question bank classified by topic, difficulty, and status.

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
2. Start services: `docker compose up --build`
3. Frontend: [http://localhost:3000](http://localhost:3000)
4. API health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
5. API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

For local development, the backend container applies Alembic migrations at startup. Stop services with `docker compose down`. Add `-v` only when you intend to delete the local PostgreSQL data volume.

## Create an instructor account

Public registration can only create student accounts. Create instructor/admin accounts only from a trusted terminal after the backend is running:

```bash
docker compose exec backend python -m app.cli create-privileged-user --role instructor --email instructor@example.edu --full-name "Course Instructor"
```

The command prompts for the password twice without echoing it. This command is a local/trusted-operator tool, not an API endpoint.

## Main API routes

All routes use the `/api/v1` prefix.

| Method | Route | Access |
|---|---|---|
| POST | `/auth/register` | Public; creates student |
| POST | `/auth/login` | Public |
| GET | `/auth/me` | Authenticated |
| POST | `/courses` | Instructor |
| GET | `/courses` | Own courses / enrolled courses / admin list |
| GET, PATCH | `/courses/{id}` | Course owner, enrolled student (GET), or admin |
| POST | `/courses/enroll` | Student with a join code |
| GET | `/courses/{id}/students` | Course instructor or admin |
| GET, POST | `/courses/{id}/topics` | Course participants (GET); instructor/admin (POST) |
| PATCH, DELETE | `/courses/{id}/topics/{topic_id}` | Instructor/admin; topics with questions cannot be deleted |
| GET, POST | `/courses/{id}/questions` | Instructor/admin |
| GET, PATCH, DELETE | `/courses/{id}/questions/{question_id}` | Instructor/admin |

Question-bank items are single-choice multiple-choice questions with 2–6 options and exactly one correct option. Options and answer keys are currently restricted to course instructors/admins; students will receive assessment-safe question views in the quiz phase.

## Run checks

Backend (Python 3.12+):

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff check app tests alembic
alembic upgrade head --sql
pytest
```

Frontend (Node.js 24 LTS or another compatible supported release):

```bash
cd frontend
npm install
npm run lint
npm run typecheck
npm run build
```

## Important security boundary

Local credentials in `.env.example` are not production secrets. Production needs managed secrets, TLS, backups, rate limiting, account recovery/verification, security review, and a suitable student-data privacy policy. The current scaffold is not ready for real student data.
