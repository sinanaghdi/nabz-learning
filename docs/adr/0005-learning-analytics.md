# ADR 0005: Course and Topic Learning Analytics

- Status: Accepted for the pilot
- Date: 2026-10-11

## Context

Assessment scores alone do not tell an instructor which learning topics need another explanation. The pilot needs small, interpretable reports from submitted attempts without introducing an analytics platform or AI dependency.

## Decision

- Add instructor/admin-only course overview, topic accuracy, and enrolled-student summary endpoints.
- Include only submitted attempts in score-based reports.
- Count each included question as a presentation when an attempt is submitted; unanswered questions count as not correct for topic accuracy.
- Return null accuracy for topics without question presentations rather than treating missing data as zero knowledge.
- Mark a topic needs_review only when at least three presentations exist and accuracy is below 60%.
- Keep the threshold rule explicit and documented; do not describe it as an AI prediction.
- Do not add a database migration: the reports aggregate existing course, question, attempt, answer and enrollment tables.

## Consequences

The first pilot can compare course performance, inspect student result summaries, and identify topics with repeated low accuracy. The reports are available through OpenAPI and can later power Persian RTL dashboards.

## Risks and follow-up

Topic calculations currently use current question answer keys. Editing a question after student attempts may alter historical topic accuracy. Add immutable question versions or assessment-time answer snapshots before high-stakes use. Dashboard charts, exports, privacy controls for data sharing and analytics validation with instructors remain separate follow-up work.
