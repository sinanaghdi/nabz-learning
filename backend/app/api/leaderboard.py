from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.course_access import ensure_course_access, get_course_or_404
from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.assessments import Assessment, AttemptStatus, QuizAttempt
from app.models.course import Enrollment
from app.models.user import User, UserRole
from app.schemas.leaderboard import LeaderboardEntryRead

router = APIRouter(tags=["leaderboard"])


@router.get(
    "/courses/{course_id}/leaderboard",
    response_model=list[LeaderboardEntryRead],
    summary="Get course leaderboard from submitted assessment attempts",
)
def get_course_leaderboard(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LeaderboardEntryRead]:
    course = get_course_or_404(db, course_id)
    ensure_course_access(course, current_user, db)

    attempt_stats = (
        select(
            QuizAttempt.student_id.label("student_id"),
            func.count(QuizAttempt.id).label("submitted_attempts"),
            func.avg(QuizAttempt.score_percent).label("average_score_percent"),
            func.max(QuizAttempt.score_percent).label("best_score_percent"),
            func.max(QuizAttempt.submitted_at).label("last_submitted_at"),
        )
        .join(Assessment, Assessment.id == QuizAttempt.assessment_id)
        .where(
            Assessment.course_id == course_id,
            QuizAttempt.status == AttemptStatus.SUBMITTED.value,
            QuizAttempt.score_percent.is_not(None),
        )
        .group_by(QuizAttempt.student_id)
        .subquery()
    )
    rows = db.execute(
        select(
            User.id,
            User.full_name,
            attempt_stats.c.submitted_attempts,
            attempt_stats.c.average_score_percent,
            attempt_stats.c.best_score_percent,
            attempt_stats.c.last_submitted_at,
        )
        .join(Enrollment, Enrollment.student_id == User.id)
        .outerjoin(attempt_stats, attempt_stats.c.student_id == User.id)
        .where(Enrollment.course_id == course_id, User.is_active.is_(True))
    ).all()

    ordered = sorted(
        rows,
        key=lambda row: (
            row.average_score_percent is None,
            -(float(row.average_score_percent or 0)),
            -(int(row.submitted_attempts or 0)),
            -(float(row.best_score_percent or 0)),
            row.full_name.casefold(),
        ),
    )
    can_view_names = current_user.role in {
        UserRole.INSTRUCTOR.value,
        UserRole.ADMIN.value,
    }
    ranked_count = 0
    result: list[LeaderboardEntryRead] = []
    for row in ordered:
        has_score = row.average_score_percent is not None
        rank = None
        if has_score:
            ranked_count += 1
            rank = ranked_count

        if can_view_names:
            display_name = row.full_name
        elif row.id == current_user.id:
            display_name = "شما"
        elif rank is not None:
            localized_rank = str(rank).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
            display_name = f"دانشجوی رتبهٔ {localized_rank}"
        else:
            display_name = "دانشجوی بدون رتبه"

        result.append(
            LeaderboardEntryRead(
                rank=rank,
                display_name=display_name,
                submitted_attempts=int(row.submitted_attempts or 0),
                average_score_percent=(
                    float(row.average_score_percent)
                    if row.average_score_percent is not None
                    else None
                ),
                best_score_percent=(
                    float(row.best_score_percent)
                    if row.best_score_percent is not None
                    else None
                ),
                last_submitted_at=row.last_submitted_at,
                is_current_user=row.id == current_user.id,
            )
        )
    return result
