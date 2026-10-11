from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Course, Enrollment
from app.models.user import User, UserRole


def get_course_or_404(db: Session, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    return course


def ensure_course_manager(course: Course, user: User) -> None:
    """Only the assigned instructor or an administrator can manage course content."""
    if user.role == UserRole.ADMIN.value:
        return
    if user.role == UserRole.INSTRUCTOR.value and course.instructor_id == user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only the course instructor or an administrator can manage this course.",
    )


def ensure_course_access(course: Course, user: User, db: Session) -> None:
    """Permit the course instructor, an admin, or an enrolled student to read a course."""
    if user.role == UserRole.ADMIN.value:
        return
    if user.role == UserRole.INSTRUCTOR.value and course.instructor_id == user.id:
        return
    if user.role == UserRole.STUDENT.value:
        enrollment_id = db.scalar(
            select(Enrollment.id).where(
                Enrollment.course_id == course.id,
                Enrollment.student_id == user.id,
            )
        )
        if enrollment_id is not None:
            return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this course.",
    )
