# Pilot Security and Operations Checklist

This checklist separates code controls from operational work still required. CI passing is not a production security certification.

## Implemented in the current code

- [x] Public registration creates student accounts only.
- [x] Passwords are hashed with Argon2.
- [x] Bearer tokens are signed, issuer-checked, and expire.
- [x] Disabled accounts are rejected by authenticated API dependencies.
- [x] Course ownership and enrollment checks protect course-scoped operations.
- [x] Student assessment payloads omit correctness flags and explanations.
- [x] Answer writes validate attempt ownership, assessment membership, and option/question association.
- [x] Submitted attempts cannot be submitted twice.
- [x] An in-progress attempt and its saved answers can be recovered by the same student.
- [x] Repeated start requests reuse an in-progress attempt.
- [x] Regression tests cover attempt ownership and cross-question option tampering.

## Required before real student data

- [ ] Replace local JWT/database credentials with managed deployment secrets.
- [ ] Enforce HTTPS end-to-end and configure trusted proxy/host behavior.
- [ ] Add distributed rate limits for login and registration, with monitoring.
- [ ] Decide on email verification, account recovery, instructor verification, and support procedures.
- [ ] Set an explicit retention/deletion policy for student accounts, answers, scores, and analytics.
- [ ] Publish a student-data privacy notice and limit exports to authorized staff.
- [ ] Configure encrypted automated backups and perform a successful restore drill.
- [ ] Centralize logs without recording passwords, bearer tokens, or sensitive response bodies.
- [ ] Configure health checks, uptime/error monitoring, and incident response.
- [ ] Review CORS origins and database/network exposure against the deployment topology.
- [ ] Add question snapshots/versioning before high-stakes assessments.
- [ ] Review attempt-limit concurrency with the production database and rehearse migrations/rollback.
- [ ] Run application-security and dependency audits against the deployment environment.

## Pilot constraints

- Begin with one instructor, one course, and a small group of consenting students.
- Use low-stakes formative quizzes while question snapshots/versioning is absent.
- Keep a manual backup of pilot results during early testing.
- Share course enrollment codes privately with intended students.
- Stop the pilot if student data crosses accounts or backups cannot be restored.
