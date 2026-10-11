# Nabz Learning

A Persian-first learning support platform for university courses.

Nabz Learning starts with a deliberately small pilot: one instructor, one course, and a feedback loop that helps identify topic-level learning gaps.

## Phase 1 status

This branch establishes the architecture and local development foundation. It is a scaffold, not a production-ready learning platform. Authentication, course management, question banks, assessments, and learning analytics are planned for later phases.

## Technology

- **Frontend:** Next.js 16, React, TypeScript, Persian RTL
- **Backend:** FastAPI, Pydantic Settings, SQLAlchemy 2
- **Database:** PostgreSQL
- **Schema migrations:** Alembic
- **Local environment:** Docker Compose
- **CI:** GitHub Actions

## Run locally

Requirements: Docker Desktop with Docker Compose.

1. Copy the environment template:
   - macOS/Linux: `cp .env.example .env`
   - Windows PowerShell: `Copy-Item .env.example .env`
2. Start the services: `docker compose up --build`
3. Open the frontend at [http://localhost:3000](http://localhost:3000).
4. Check the API at [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health).
5. Open interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs).

To stop the services, press `Ctrl+C`, then run `docker compose down`. Add `-v` only when you intend to delete the local PostgreSQL data volume.

## Run checks

Backend checks (from the repository root, with Python 3.12+):

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff check app tests
pytest
```

Frontend checks (from the repository root, with Node.js 24 LTS or another compatible supported release):

```bash
cd frontend
npm install
npm run lint
npm run typecheck
npm run build
```

## Repository map

- `backend/`: FastAPI app, database setup, migrations, and tests
- `frontend/`: Next.js Persian RTL application
- `docs/ARCHITECTURE.md`: System boundaries and data flow
- `docs/adr/`: Architecture decision records
- `.github/workflows/`: Continuous integration
- `docker-compose.yml`: Local service orchestration
- `.env.example`: Local development configuration template

## Product rule

Build and validate the core loop before expanding scope: an instructor prepares a practice quiz, students answer, and the instructor sees which topics need more explanation. Rankings, job matching, research opportunities, and complex recommendations are out of scope until the pilot validates the core value.

## Security notes

The credentials in the Compose configuration are for local development only. Do not reuse them in a hosted environment. Never commit a real `.env` file, access token, private key, or student-identifying data. Production deployment requires separate secrets, access control, backup, privacy, and security reviews.
