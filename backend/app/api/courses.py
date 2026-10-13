import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.course_access import ensure_course_access, ensure_course_manager, get_course_or_404
from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.course import Course, CourseTopic, Enrollment, Question
from app.models.user import User, UserRole
from app.schemas.courses import (
    CourseCreate,
    CourseCreatedRead,
    CourseRead,
    CourseStudentRead,
    CourseUpdate,
    EnrollmentCreate,
    EnrollmentRead,
    TopicCreate,
    TopicRead,
    TopicUpdate,
)

router = APIRouter(tags=["courses"])



@router.post(
    "/courses",
    response_model=CourseCreatedRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a course",
)
def create_course(
    payload: CourseCreate,
    current_user: User = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> CourseCreatedRead:
    course = Course(
        instructor_id=current_user.id,
        title=payload.title,
        description=payload.description,
        term=payload.term,
        enrollment_code=secrets.token_hex(8).upper(),
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return CourseCreatedRead.model_validate(course)


@router.get("/courses", response_model=list[CourseRead], summary="List courses visible to me")
def list_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CourseRead]:
    if current_user.role == UserRole.ADMIN.value:
        statement = select(Course).order_by(Course.created_at.desc())
    elif current_user.role == UserRole.INSTRUCTOR.value:
        statement = (
            select(Course)
            .where(Course.instructor_id == current_user.id)
            .order_by(Course.created_at.desc())
        )
    else:
        statement = (
            select(Course)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(Enrollment.student_id == current_user.id)
            .order_by(Course.created_at.desc())
        )
    return [CourseRead.model_validate(course) for course in db.scalars(statement).all()]


@router.get("/courses/{course_id}", response_model=CourseRead, summary="Get course details")
def get_course(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CourseRead:
    course = get_course_or_404(db, course_id)
    ensure_course_access(course, current_user, db)
    return CourseRead.model_validate(course)


@router.patch("/courses/{course_id}", response_model=CourseRead, summary="Update a course")
def update_course(
    course_id: int,
    payload: CourseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CourseRead:
    course = get_course_or_404(db, course_id)
    ensure_course_manager(course, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "title" and value is not None:
            value = " ".join(value.split())
            if len(value) < 2:
                raise HTTPException(status_code=422, detail="Course title is too short.")
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    return CourseRead.model_validate(course)


@router.post(
    "/courses/enroll",
    response_model=EnrollmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Join a course using its enrollment code",
)
def enroll_in_course(
    payload: EnrollmentCreate,
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
) -> EnrollmentRead:
    course = db.scalar(
        select(Course).where(
            Course.enrollment_code == payload.enrollment_code,
            Course.is_active.is_(True),
        )
    )
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active course matches this enrollment code.",
        )

    existing = db.scalar(
        select(Enrollment.id).where(
            Enrollment.course_id == course.id,
            Enrollment.student_id == current_user.id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already enrolled in this course.",
        )

    enrollment = Enrollment(course_id=course.id, student_id=current_user.id)
    db.add(enrollment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already enrolled in this course.",
        ) from None
    db.refresh(enrollment)
    return EnrollmentRead.model_validate(enrollment)


@router.get(
    "/courses/{course_id}/students",
    response_model=list[CourseStudentRead],
    summary="List enrolled students",
)
def list_course_students(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CourseStudentRead]:
    course = get_course_or_404(db, course_id)
    ensure_course_manager(course, current_user)
    rows = db.execute(
        select(User, Enrollment.enrolled_at)
        .join(Enrollment, Enrollment.student_id == User.id)
        .where(Enrollment.course_id == course_id)
        .order_by(Enrollment.enrolled_at.asc())
    ).all()
    return [
        CourseStudentRead(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=UserRole(user.role),
            enrolled_at=enrolled_at,
        )
        for user, enrolled_at in rows
    ]


@router.post(
    "/courses/{course_id}/topics",
    response_model=TopicRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a course topic",
)
def create_topic(
    course_id: int,
    payload: TopicCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TopicRead:
    course = get_course_or_404(db, course_id)
    ensure_course_manager(course, current_user)
    topic = CourseTopic(
        course_id=course_id,
        title=" ".join(payload.title.split()),
        description=payload.description,
        sort_order=payload.sort_order,
    )
    db.add(topic)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A topic with this title already exists in this course.",
        ) from None
    db.refresh(topic)
    return TopicRead.model_validate(topic)


@router.get(
    "/courses/{course_id}/topics",
    response_model=list[TopicRead],
    summary="List course topics",
)
def list_topics(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TopicRead]:
    course = get_course_or_404(db, course_id)
    ensure_course_access(course, current_user, db)
    topics = db.scalars(
        select(CourseTopic)
        .where(CourseTopic.course_id == course_id)
        .order_by(CourseTopic.sort_order, CourseTopic.id)
    ).all()
    return [TopicRead.model_validate(topic) for topic in topics]


@router.patch(
    "/courses/{course_id}/topics/{topic_id}",
    response_model=TopicRead,
    summary="Update a course topic",
)
def update_topic(
    course_id: int,
    topic_id: int,
    payload: TopicUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TopicRead:
    course = get_course_or_404(db, course_id)
    ensure_course_manager(course, current_user)
    topic = db.scalar(
        select(CourseTopic).where(
            CourseTopic.id == topic_id,
            CourseTopic.course_id == course_id,
        )
    )
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "title" and value is not None:
            value = " ".join(value.split())
        setattr(topic, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A topic with this title already exists in this course.",
        ) from None
    db.refresh(topic)
    return TopicRead.model_validate(topic)


@router.delete(
    "/courses/{course_id}/topics/{topic_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an unused course topic",
)
def delete_topic(
    course_id: int,
    topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    course = get_course_or_404(db, course_id)
    ensure_course_manager(course, current_user)
    topic = db.scalar(
        select(CourseTopic).where(
            CourseTopic.id == topic_id,
            CourseTopic.course_id == course_id,
        )
    )
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found.")
    question_exists = db.scalar(
        select(Question.id).where(Question.topic_id == topic_id).limit(1)
    )
    if question_exists is not None:
        raise HTTPException(
            status_code=409,
            detail="This topic contains questions. Move or delete them before deleting the topic.",
        )
    db.delete(topic)
    db.commit()
    return None
