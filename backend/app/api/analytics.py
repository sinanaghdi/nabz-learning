from fastapi import APIRouter, Depends
from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.orm import Session

from app.api.course_access import ensure_course_manager, get_course_or_404
from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.assessments import (
    Assessment,
    AssessmentQuestion,
    AssessmentStatus,
    AttemptAnswer,
    AttemptStatus,
    QuizAttempt,
)
from app.models.course import CourseTopic, Enrollment, Question, QuestionOption
from app.models.user import User
from app.schemas.analytics import (
    CourseAnalyticsOverview,
    StudentLearningSummary,
    TopicLearningAnalytics,
)

router = APIRouter(tags=["learning analytics"])

MIN_PRESENTATIONS_FOR_REVIEW = 3
REVIEW_ACCURACY_THRESHOLD = 60.0
AVAILABLE_ASSESSMENT_STATUSES = (
    AssessmentStatus.PUBLISHED.value,
    AssessmentStatus.CLOSED.value,
)


def percentage(value: float | int | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


@router.get(
    "/courses/{course_id}/analytics/overview",
    response_model=CourseAnalyticsOverview,
    summary="Summarize submitted assessment results for a course",
)
def get_course_analytics_overview(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CourseAnalyticsOverview:
    course = get_course_or_404(db, course_id)
    ensure_course_manager(course, current_user)

    enrolled_students = db.scalar(
        select(func.count(Enrollment.id)).where(Enrollment.course_id == course_id)
    ) or 0
    published_assessments = db.scalar(
        select(func.count(Assessment.id)).where(
            Assessment.course_id == course_id,
            Assessment.status.in_(AVAILABLE_ASSESSMENT_STATUSES),
        )
    ) or 0
    result = db.execute(
        select(
            func.count(QuizAttempt.id),
            func.count(distinct(QuizAttempt.student_id)),
            func.avg(QuizAttempt.score_percent),
            func.max(QuizAttempt.score_percent),
            func.min(QuizAttempt.score_percent),
        )
        .join(Assessment, Assessment.id == QuizAttempt.assessment_id)
        .where(
            Assessment.course_id == course_id,
            QuizAttempt.status == AttemptStatus.SUBMITTED.value,
        )
    ).one()
    return CourseAnalyticsOverview(
        course_id=course.id,
        course_title=course.title,
        enrolled_students=int(enrolled_students),
        published_assessments=int(published_assessments),
        submitted_attempts=int(result[0] or 0),
        students_with_submissions=int(result[1] or 0),
        average_score_percent=percentage(result[2]),
        best_score_percent=percentage(result[3]),
        lowest_score_percent=percentage(result[4]),
    )


@router.get(
    "/courses/{course_id}/analytics/topics",
    response_model=list[TopicLearningAnalytics],
    summary="Report topic-level accuracy and topics that may need review",
)
def get_topic_learning_analytics(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TopicLearningAnalytics]:
    course = get_course_or_404(db, course_id)
    ensure_course_manager(course, current_user)

    correct_answer = case((QuestionOption.id.is_not(None), 1), else_=0)
    rows = db.execute(
        select(
            CourseTopic.id,
            CourseTopic.title,
            func.count(QuizAttempt.id),
            func.coalesce(func.sum(correct_answer), 0),
        )
        .select_from(CourseTopic)
        .outerjoin(Question, Question.topic_id == CourseTopic.id)
        .outerjoin(AssessmentQuestion, AssessmentQuestion.question_id == Question.id)
        .outerjoin(
            Assessment,
            and_(
                Assessment.id == AssessmentQuestion.assessment_id,
                Assessment.course_id == course_id,
                Assessment.status.in_(AVAILABLE_ASSESSMENT_STATUSES),
            ),
        )
        .outerjoin(
            QuizAttempt,
            and_(
                QuizAttempt.assessment_id == Assessment.id,
                QuizAttempt.status == AttemptStatus.SUBMITTED.value,
            ),
        )
        .outerjoin(
            AttemptAnswer,
            and_(
                AttemptAnswer.attempt_id == QuizAttempt.id,
                AttemptAnswer.question_id == Question.id,
            ),
        )
        .outerjoin(
            QuestionOption,
            and_(
                QuestionOption.id == AttemptAnswer.selected_option_id,
                QuestionOption.question_id == Question.id,
                QuestionOption.is_correct.is_(True),
            ),
        )
        .where(CourseTopic.course_id == course_id)
        .group_by(CourseTopic.id, CourseTopic.title, CourseTopic.sort_order)
        .order_by(CourseTopic.sort_order, CourseTopic.id)
    ).all()

    report: list[TopicLearningAnalytics] = []
    for topic_id, title, presentations, correct in rows:
        presentations = int(presentations or 0)
        correct = int(correct or 0)
        accuracy = percentage(correct * 100 / presentations) if presentations else None
        report.append(
            TopicLearningAnalytics(
                topic_id=topic_id,
                topic_title=title,
                question_presentations=presentations,
                correct_responses=correct,
                accuracy_percent=accuracy,
                needs_review=(
                    presentations >= MIN_PRESENTATIONS_FOR_REVIEW
                    and accuracy is not None
                    and accuracy < REVIEW_ACCURACY_THRESHOLD
                ),
            )
        )
    return report


@router.get(
    "/courses/{course_id}/analytics/students",
    response_model=list[StudentLearningSummary],
    summary="Summarize submitted attempts for enrolled students",
)
def get_student_learning_summaries(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[StudentLearningSummary]:
    course = get_course_or_404(db, course_id)
    ensure_course_manager(course, current_user)

    rows = db.execute(
        select(
            User.id,
            User.full_name,
            User.email,
            func.count(QuizAttempt.id),
            func.avg(QuizAttempt.score_percent),
            func.max(QuizAttempt.score_percent),
            func.max(QuizAttempt.submitted_at),
        )
        .select_from(Enrollment)
        .join(User, User.id == Enrollment.student_id)
        .outerjoin(
            Assessment,
            and_(
                Assessment.course_id == course_id,
                Assessment.status.in_(AVAILABLE_ASSESSMENT_STATUSES),
            ),
        )
        .outerjoin(
            QuizAttempt,
            and_(
                QuizAttempt.assessment_id == Assessment.id,
                QuizAttempt.student_id == User.id,
                QuizAttempt.status == AttemptStatus.SUBMITTED.value,
            ),
        )
        .where(Enrollment.course_id == course_id)
        .group_by(User.id, User.full_name, User.email)
        .order_by(User.full_name, User.id)
    ).all()
    return [
        StudentLearningSummary(
            student_id=row[0],
            full_name=row[1],
            email=row[2],
            submitted_attempts=int(row[3] or 0),
            average_score_percent=percentage(row[4]),
            best_score_percent=percentage(row[5]),
            last_submitted_at=row[6],
        )
        for row in rows
    ]
