# ADR 0004: Assessments and Quiz Attempts

- **Status:** Accepted for pilot
- **Date:** 2026-10-11

## Context

The pilot needs a complete learning loop after course enrollment and question-bank authoring: instructors compose quizzes from course questions, students answer them, and the system produces a repeatable objective score.

## Decision

- An assessment belongs to one course and begins as a draft.
- Assessment question order is persisted explicitly.
- Only published question-bank items belonging to the same course can be attached.
- Students see only published assessments in courses where they are enrolled.
- Student-safe response schemas intentionally exclude correct-answer flags and explanations.
- Attempts track the student, attempt number, start/submission timestamps and score.
- Each answer references an assessment question and a selected option; the API validates both relationships.
- Submitted assessments are automatically scored server-side using single-choice answer keys.
- A draft assessment must contain at least one question before publishing.
- This phase exposes APIs; the dedicated Persian RTL assessment UI follows later.

## Consequences

The pilot can execute the instructor-to-student assessment workflow and store results for future topic-level analytics. The implementation deliberately does not add randomization, manual grading, open/close windows, or an LMS-style assignment center.

## Risks and follow-up

Published question content is not snapshotted yet, so instructors should avoid modifying questions used by published assessments. Attempt-limit checks need stronger concurrency guarantees before high-volume use. Production deployment requires further security, privacy, operational and accessibility review.
