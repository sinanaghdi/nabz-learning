# ADR 0003: Course Ownership and Question Bank

- **Status:** Accepted for the pilot
- **Date:** 2026-10-11

## Context

The pilot needs a course boundary for content ownership and student access. Questions must be organized by learning topic so later quiz results can be aggregated by topic.

## Decision

- An instructor owns each course.
- Students enroll using a unique, randomly generated course join code.
- Enrollment is represented by a dedicated table with a unique course/student pair.
- Each course contains ordered topics.
- The first question type is single-choice MCQ, with 2–6 options and exactly one correct answer.
- Questions have difficulty and lifecycle status fields.
- Question-bank endpoints are instructor/admin-only and never serve answer keys to students.
- Create instructor/admin accounts through a trusted CLI command, never public registration.

## Consequences

The model supports course-level authorization and future topic-based analytics while keeping the pilot intentionally narrow. Join codes are a convenience, not proof of university identity. They can be forwarded, so production use may need enrollment approval or university identity verification.

## Deferred

Multi-answer questions, free-text questions, media attachments, randomization, quiz attempts, grading, and analytics require separate domain decisions and tests.
