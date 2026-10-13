# Nabz Learning — Architecture Overview

**Status:** MVP phases 1–7 merged; interactive demo deployed, integrated application local-only  
**Architecture style:** Modular monolith  
**Pilot:** One instructor, one course, and a small student cohort

## Product loop

1. An instructor creates a course and shares its enrollment code.
2. Students enroll using the code.
3. The instructor organizes topics and publishes single-choice questions.
4. The instructor assembles and publishes an assessment.
5. Students start or resume an attempt, save answers, and submit.
6. The API grades objective questions and persists results.
7. Instructor analytics aggregate submitted attempts into course and topic summaries.
8. Students and instructors browse opportunities for jobs, internships, projects, and research; instructors/admins moderate publication.

## Modules

- `frontend/`: Next.js App Router, TypeScript, Persian-first RTL presentation.
- `backend/app/api/auth.py`: student registration, login, and current account.
- `backend/app/api/courses.py`: course CRUD, enrollment, roster, and topics.
- `backend/app/api/questions.py`: course-scoped question-bank operations.
- `backend/app/api/assessments.py`: assessment lifecycle, answer-safe delivery, attempts, resume, and scoring.
- `backend/app/api/opportunities.py`: opportunity submissions, moderation, and status transitions.
- `backend/app/api/leaderboard.py` (or the route module exposing leaderboard endpoints): course ranking from submitted attempts with student name masking.
- `backend/app/api/course_access.py`: reusable course ownership and enrollment checks.
- `backend/app/models/`: SQLAlchemy domain models.
- `backend/app/schemas/`: explicit request/response DTOs.
- `backend/alembic/versions/`: versioned database migrations.
- `backend/tests/`: isolated API and authorization tests.
- `docs/adr/`: architecture decision records.

## Authorization and answer-key protection

- Public registration creates student accounts only; privileged accounts are provisioned through the CLI.
- Only the course owner or an administrator can author or publish course assessments.
- Students must be enrolled to see published assessments or start attempts.
- Student assessment payloads omit correctness flags and question explanations.
- Students can read, answer, and submit only their own attempts.
- Selected options must belong to the answered question, and the question must belong to the assessment.
- A submitted attempt cannot be submitted a second time; the server computes scores.
- Repeated start requests reuse an unfinished attempt rather than consuming another attempt.
- Active-attempt recovery is scoped to the authenticated student and their course enrollment.

## Data model

- `users`, `courses`, `enrollments`, `course_topics`, `questions`, `question_options`
- `assessments`: course, title, status, duration, and attempt limit.
- `assessment_questions`: ordered association to published questions from the same course.
- `quiz_attempts`: student, attempt number, lifecycle state, and score.
- `attempt_answers`: one replaceable selected option per question per attempt.

Alembic migrations create the user, course/question-bank, and assessment/attempt tables in sequence.

## Reliability behavior

- Attempts and selected answers are persisted server-side.
- The student dashboard queries for the current student's unfinished attempt and restores saved choices.
- Repeating the start request returns the same active attempt with HTTP 200.
- The active-attempt endpoint returns `null` when the student has no unfinished attempt.
- The API never returns another student's attempt through the active-attempt endpoint.

## Current limitations

This is a pilot-oriented application, not a production-ready service. Grading currently supports single-choice questions. Question snapshots/versioning are not implemented, so changing a question after it has been used may alter historical interpretation. Production still needs managed secrets, HTTPS, login rate limiting, account recovery/verification, backup-and-restore drills, privacy review, logging/monitoring, deployment controls, and further concurrency review for attempt limits.

## Deferred work

Question snapshots/versioning, richer question types, manual grading, randomized question/option order, scheduled opening/closing, token refresh, email verification, password reset, production privacy/security review, deterministic frontend dependency locking, browser-level end-to-end tests, rate limiting for authentication and enrollment-code lookup, and public deployment of the integrated app remain future work.
