from datetime import datetime

from pydantic import BaseModel


class CourseAnalyticsOverview(BaseModel):
    course_id: int
    course_title: str
    enrolled_students: int
    published_assessments: int
    submitted_attempts: int
    students_with_submissions: int
    average_score_percent: float | None
    best_score_percent: float | None
    lowest_score_percent: float | None


class TopicLearningAnalytics(BaseModel):
    topic_id: int
    topic_title: str
    question_presentations: int
    correct_responses: int
    accuracy_percent: float | None
    needs_review: bool


class StudentLearningSummary(BaseModel):
    student_id: int
    full_name: str
    email: str
    submitted_attempts: int
    average_score_percent: float | None
    best_score_percent: float | None
    last_submitted_at: datetime | None
