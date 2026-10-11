# Nabz Learning — Architecture Overview

**Status:** Phase 4 — assessments and attempts  
**Architecture style:** Modular monolith  
**Pilot:** One instructor, one course, and a small student cohort

## Product loop

1. An instructor creates a course and shares its enrollment code.
2. Students enroll using the code.
3. The instructor organizes course topics and publishes single-choice questions.
4. The instructor assembles and publishes an assessment.
5. Enrolled students start an attempt, save answers, and submit.
6. The API grades objective questions and persists the result.
7. Phase 5 will aggregate results by learning topic for the instructor.

## Modules

- \`frontend/\`: Next.js App Router, TypeScript, Persian-first RTL presentation.
- \`backend/app/api/auth.py\`: registration, login and current account.
- \`backend/app/api/courses.py\`: courses, enrollments, roster and topics.
- \`backend/app/api/questions.py\`: course-scoped question-bank CRUD.
- \`backend/app/api/assessments.py\`: assessment lifecycle, safe question delivery, attempts and scoring.
- \`backend/app/api/course_access.py\`: reusable course ownership and enrollment checks.
- \`backend/app/models/\`: SQLAlchemy domain models.
- \`backend/app/schemas/\`: explicit request/response DTOs.
- \`backend/alembic/versions/\`: versioned database migrations.
- \`backend/tests/\`: isolated API tests.
- \`docs/adr/\`: architecture decisions.

## Authorization and answer-key protection

- Public registration only creates student accounts.
- Only the course owner or an administrator can author, edit or publish assessments.
- Students must be enrolled to see published assessments and start attempts.
- Students never receive option correctness flags or question explanations in assessment responses.
- Students may only read, answer and submit their own attempt.
- Selected options must belong to the answered question, and the question must belong to that assessment.
- An assessment can only be published if it contains at least one question.
- Only draft assessments can be edited; a submitted attempt cannot be submitted twice.

## Data model

- \`users\`, \`courses\`, \`enrollments\`, \`course_topics\`, \`questions\`, \`question_options\`
- \`assessments\`: course, title, status, duration and attempt limit.
- \`assessment_questions\`: ordered association to published questions from the same course.
- \`quiz_attempts\`: student, attempt number, lifecycle state and score.
- \`attempt_answers\`: one replaceable selected option per question per attempt.

Migration \`20261011_0003\` adds the assessment, attempt and answer tables after course/question-bank migrations.

## Current limitations

The UI dashboards have not yet been built; endpoints are available through local OpenAPI docs. Current scoring is objective single-choice auto-grading. The course pilot assumes instructors do not edit published question content after using it in a published assessment; question snapshots/versioning is a future hardening item. Max-attempt enforcement is suitable for a small pilot but must be reviewed for concurrent requests before high-volume use.

## Deferred

Topic-level analytics, instructor reporting, manual grading, randomized questions/options, question versioning/snapshots, opening/closing schedules, email verification, password reset, token refresh, rate limits, production privacy/security review, and user-facing RTL screens remain future work.
