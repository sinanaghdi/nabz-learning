# Nabz Learning — Architecture Overview

**Status:** Phase 5 — learning analytics  
**Architecture style:** Modular monolith  
**Pilot:** One instructor, one course, and a small student cohort

## Product loop

1. An instructor creates a course and shares its enrollment code.
2. Students enroll using the code.
3. The instructor organizes topics and publishes single-choice questions.
4. The instructor assembles and publishes an assessment.
5. Enrolled students start an attempt, save answers, and submit.
6. The API grades objective questions and persists the result.
7. Instructors review course results, student summaries and per-topic accuracy.

## Modules

- frontend/: Next.js App Router, TypeScript, Persian-first RTL presentation.
- backend/app/api/auth.py: registration, login and current account.
- backend/app/api/courses.py: courses, enrollments, roster and topics.
- backend/app/api/questions.py: course-scoped question-bank CRUD.
- backend/app/api/assessments.py: assessment lifecycle, answer-safe question delivery, attempts and scoring.
- backend/app/api/analytics.py: course overview, topic accuracy and enrolled-student summaries.
- backend/app/api/course_access.py: reusable course ownership and enrollment checks.
- backend/app/models/: SQLAlchemy domain models.
- backend/app/schemas/: explicit request/response DTOs.
- backend/alembic/versions/: versioned database migrations.
- backend/tests/: isolated API tests.
- docs/adr/: architecture decisions.

## Analytics definitions

- Submitted attempt: only attempts with status submitted are included in score-based reports.
- Course average: arithmetic mean of persisted attempt percentages.
- Question presentation: a question included in a submitted assessment attempt counts once, including unanswered questions.
- Topic accuracy: correct responses divided by question presentations; topics without presentations return null accuracy instead of zero.
- Needs review: accuracy below 60% after at least three question presentations. This is a pilot heuristic, not an AI diagnosis.
- Student summary: includes all enrolled students; students without submitted attempts have zero attempts and null score metrics.
- Published assessments in the overview means assessments in published or closed status, including those previously made available to students.

## Access and data safety

- Only the course owner or an administrator can view analytics.
- Students cannot use aggregate analytics routes.
- Analytics return learning metrics and enrolled-student identity to authorized instructors; avoid sharing exports outside the teaching context.
- The topic report uses the current answer key from the question bank. Editing correct answers after an assessment is taken can change historical topic accuracy; immutable question versioning/snapshots remain a required hardening item before high-stakes use.

## Current limitations

Dedicated instructor/student dashboards have not yet been built; use the local OpenAPI docs to exercise these endpoints. Topic review alerts are rule-based. The pilot still needs question snapshots, concurrency hardening, privacy review, operational monitoring, and production deployment controls.

## Deferred

Persian RTL dashboards, visualization, exports, assessment schedules, randomized questions/options, immutable question versioning, manual grading, email verification, password reset, token refresh, rate limits, institutional SSO, and production privacy/security review remain future work.
