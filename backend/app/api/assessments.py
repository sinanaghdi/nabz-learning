from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.course_access import ensure_course_access, ensure_course_manager, get_course_or_404
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
from app.models.course import CourseTopic, Question, QuestionOption
from app.models.user import User, UserRole
from app.schemas.assessments import (
    AnswerSubmission,
    AssessmentCreate,
    AssessmentDetailRead,
    AssessmentRead,
    AssessmentUpdate,
    AttemptAnswerRead,
    QuizAttemptDetailRead,
    QuizAttemptRead,
    StudentOptionRead,
    StudentQuestionRead,
)

router = APIRouter(tags=["assessments"])


def get_assessment_or_404(db: Session, course_id: int, assessment_id: int) -> Assessment:
    assessment = db.scalar(
        select(Assessment).where(
            Assessment.id == assessment_id,
            Assessment.course_id == course_id,
        )
    )
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found in this course.")
    return assessment


def get_question_bank_items(
    db: Session, course_id: int, question_ids: list[int]
) -> dict[int, Question]:
    questions = db.scalars(
        select(Question)
        .join(CourseTopic, Question.topic_id == CourseTopic.id)
        .where(
            CourseTopic.course_id == course_id,
            Question.id.in_(question_ids),
        )
        .options(selectinload(Question.options))
    ).all()
    by_id = {question.id: question for question in questions}
    if len(by_id) != len(question_ids):
        raise HTTPException(
            status_code=422,
            detail="Every selected question must belong to this course.",
        )
    if any(question.status != "published" for question in questions):
        raise HTTPException(
            status_code=422,
            detail="Only published question-bank items can be added to an assessment.",
        )
    return by_id


def count_assessment_questions(db: Session, assessment_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(AssessmentQuestion.id)).where(
                AssessmentQuestion.assessment_id == assessment_id
            )
        )
        or 0
    )


def assessment_read(db: Session, assessment: Assessment) -> AssessmentRead:
    return AssessmentRead(
        id=assessment.id,
        course_id=assessment.course_id,
        title=assessment.title,
        instructions=assessment.instructions,
        status=assessment.status,
        duration_minutes=assessment.duration_minutes,
        max_attempts=assessment.max_attempts,
        question_count=count_assessment_questions(db, assessment.id),
        created_at=assessment.created_at,
        published_at=assessment.published_at,
    )


def safe_questions(db: Session, assessment_id: int) -> list[StudentQuestionRead]:
    links = db.scalars(
        select(AssessmentQuestion)
        .where(AssessmentQuestion.assessment_id == assessment_id)
        .order_by(AssessmentQuestion.position)
    ).all()
    question_ids = [link.question_id for link in links]
    if not question_ids:
        return []
    questions = db.scalars(
        select(Question).where(Question.id.in_(question_ids)).options(selectinload(Question.options))
    ).all()
    by_id = {question.id: question for question in questions}
    return [
        StudentQuestionRead(
            id=question_id,
            prompt=by_id[question_id].prompt,
            options=[
                StudentOptionRead(id=option.id, text=option.text, position=option.position)
                for option in by_id[question_id].options
            ],
        )
        for question_id in question_ids
    ]


def get_attempt_or_404(db: Session, attempt_id: int) -> QuizAttempt:
    attempt = db.get(QuizAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    return attempt


def ensure_attempt_owner_or_manager(
    db: Session, attempt: QuizAttempt, user: User
) -> Assessment:
    assessment = db.get(Assessment, attempt.assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    course = get_course_or_404(db, assessment.course_id)
    if user.role == UserRole.STUDENT.value:
        if attempt.student_id != user.id:
            raise HTTPException(status_code=403, detail="This attempt belongs to another student.")
    else:
        ensure_course_manager(course, user)
    return assessment


def aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def ensure_attempt_is_open(attempt: QuizAttempt, assessment: Assessment) -> None:
    if attempt.status != AttemptStatus.IN_PROGRESS.value:
        raise HTTPException(status_code=409, detail="This attempt has already been submitted.")
    if assessment.duration_minutes is not None:
        deadline = aware_utc(attempt.started_at) + timedelta(minutes=assessment.duration_minutes)
        if datetime.now(UTC) >= deadline:
            raise HTTPException(
                status_code=409,
                detail="The time limit has expired. Submit the attempt.",
            )


@router.post(
    "/courses/{course_id}/assessments",
    response_model=AssessmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft assessment from published questions",
)
def create_assessment(
    course_id: int,
    payload: AssessmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssessmentRead:
    course = get_course_or_404(db, course_id)
    ensure_course_manager(course, current_user)
    get_question_bank_items(db, course_id, payload.question_ids)

    assessment = Assessment(
        course_id=course_id,
        title=payload.title,
        instructions=payload.instructions,
        duration_minutes=payload.duration_minutes,
        max_attempts=payload.max_attempts,
        status=AssessmentStatus.DRAFT.value,
    )
    assessment.question_links = [
        AssessmentQuestion(question_id=question_id, position=position)
        for position, question_id in enumerate(payload.question_ids)
    ]
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment_read(db, assessment)


@router.get(
    "/courses/{course_id}/assessments",
    response_model=list[AssessmentRead],
    summary="List course assessments visible to the current user",
)
def list_assessments(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AssessmentRead]:
    course = get_course_or_404(db, course_id)
    ensure_course_access(course, current_user, db)
    statement = select(Assessment).where(Assessment.course_id == course_id)
    if current_user.role == UserRole.STUDENT.value:
        statement = statement.where(Assessment.status == AssessmentStatus.PUBLISHED.value)
    assessments = db.scalars(statement.order_by(Assessment.created_at.desc())).all()
    return [assessment_read(db, item) for item in assessments]


@router.get(
    "/courses/{course_id}/assessments/{assessment_id}",
    response_model=AssessmentDetailRead,
    summary="Get assessment metadata and answer-key-safe questions",
)
def get_assessment(
    course_id: int,
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssessmentDetailRead:
    course = get_course_or_404(db, course_id)
    ensure_course_access(course, current_user, db)
    assessment = get_assessment_or_404(db, course_id, assessment_id)
    if (
        current_user.role == UserRole.STUDENT.value
        and assessment.status != AssessmentStatus.PUBLISHED.value
    ):
        raise HTTPException(status_code=404, detail="Assessment not found.")
    return AssessmentDetailRead(
        **assessment_read(db, assessment).model_dump(),
        questions=safe_questions(db, assessment_id),
    )


@router.patch(
    "/courses/{course_id}/assessments/{assessment_id}",
    response_model=AssessmentRead,
    summary="Update a draft assessment",
)
def update_assessment(
    course_id: int,
    assessment_id: int,
    payload: AssessmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssessmentRead:
    course = get_course_or_404(db, course_id)
    ensure_course_manager(course, current_user)
    assessment = get_assessment_or_404(db, course_id, assessment_id)
    if assessment.status != AssessmentStatus.DRAFT.value:
        raise HTTPException(status_code=409, detail="Only draft assessments can be edited.")
    changes = payload.model_dump(exclude_unset=True)
    question_ids = changes.pop("question_ids", None)
    if question_ids is not None:
        get_question_bank_items(db, course_id, question_ids)
        old_links = db.scalars(
            select(AssessmentQuestion).where(
                AssessmentQuestion.assessment_id == assessment.id
            )
        ).all()
        for link in old_links:
            db.delete(link)
        db.flush()
        db.add_all(
            AssessmentQuestion(
                assessment_id=assessment.id,
                question_id=question_id,
                position=position,
            )
            for position, question_id in enumerate(question_ids)
        )
    for field, value in changes.items():
        setattr(assessment, field, value)
    db.commit()
    db.refresh(assessment)
    return assessment_read(db, assessment)


@router.post(
    "/courses/{course_id}/assessments/{assessment_id}/publish",
    response_model=AssessmentRead,
    summary="Publish an assessment",
)
def publish_assessment(
    course_id: int,
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssessmentRead:
    course = get_course_or_404(db, course_id)
    ensure_course_manager(course, current_user)
    assessment = get_assessment_or_404(db, course_id, assessment_id)
    if assessment.status != AssessmentStatus.DRAFT.value:
        raise HTTPException(status_code=409, detail="Only draft assessments can be published.")
    if count_assessment_questions(db, assessment_id) == 0:
        raise HTTPException(status_code=409, detail="An assessment needs at least one question.")
    assessment.status = AssessmentStatus.PUBLISHED.value
    assessment.published_at = datetime.now(UTC)
    db.commit()
    db.refresh(assessment)
    return assessment_read(db, assessment)


@router.post(
    "/courses/{course_id}/assessments/{assessment_id}/attempts",
    response_model=QuizAttemptRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start a student attempt",
)
def start_attempt(
    course_id: int,
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizAttemptRead:
    if current_user.role != UserRole.STUDENT.value:
        raise HTTPException(status_code=403, detail="Only students can start an attempt.")
    course = get_course_or_404(db, course_id)
    ensure_course_access(course, current_user, db)
    assessment = get_assessment_or_404(db, course_id, assessment_id)
    if assessment.status != AssessmentStatus.PUBLISHED.value:
        raise HTTPException(status_code=409, detail="This assessment is not open for attempts.")
    question_count = count_assessment_questions(db, assessment_id)
    if question_count == 0:
        raise HTTPException(status_code=409, detail="This assessment has no questions.")

    previous_attempts = db.scalar(
        select(func.count(QuizAttempt.id)).where(
            QuizAttempt.assessment_id == assessment_id,
            QuizAttempt.student_id == current_user.id,
        )
    ) or 0
    if previous_attempts >= assessment.max_attempts:
        raise HTTPException(status_code=409, detail="You have used all allowed attempts.")
    attempt = QuizAttempt(
        assessment_id=assessment_id,
        student_id=current_user.id,
        attempt_number=previous_attempts + 1,
        question_count=question_count,
        status=AttemptStatus.IN_PROGRESS.value,
        started_at=datetime.now(UTC),
    )
    db.add(attempt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not create a new attempt.") from None
    db.refresh(attempt)
    return QuizAttemptRead.model_validate(attempt)


@router.put(
    "/attempts/{attempt_id}/answers/{question_id}",
    response_model=QuizAttemptDetailRead,
    summary="Save or replace an answer in an active attempt",
)
def save_answer(
    attempt_id: int,
    question_id: int,
    payload: AnswerSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizAttemptDetailRead:
    attempt = get_attempt_or_404(db, attempt_id)
    assessment = ensure_attempt_owner_or_manager(db, attempt, current_user)
    if current_user.role != UserRole.STUDENT.value or attempt.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the attempt owner can answer questions.")
    ensure_attempt_is_open(attempt, assessment)

    assessment_question = db.scalar(
        select(AssessmentQuestion.id).where(
            AssessmentQuestion.assessment_id == assessment.id,
            AssessmentQuestion.question_id == question_id,
        )
    )
    if assessment_question is None:
        raise HTTPException(status_code=422, detail="This question is not part of the assessment.")
    option = db.get(QuestionOption, payload.selected_option_id)
    if option is None or option.question_id != question_id:
        raise HTTPException(
            status_code=422,
            detail="Selected option does not belong to this question.",
        )

    answer = db.scalar(
        select(AttemptAnswer).where(
            AttemptAnswer.attempt_id == attempt.id,
            AttemptAnswer.question_id == question_id,
        )
    )
    if answer is None:
        answer = AttemptAnswer(
            attempt_id=attempt.id,
            question_id=question_id,
            selected_option_id=payload.selected_option_id,
        )
        db.add(answer)
    else:
        answer.selected_option_id = payload.selected_option_id
    db.commit()
    db.refresh(attempt)
    return build_attempt_detail(db, attempt)


def build_attempt_detail(db: Session, attempt: QuizAttempt) -> QuizAttemptDetailRead:
    answers = db.scalars(
        select(AttemptAnswer)
        .where(AttemptAnswer.attempt_id == attempt.id)
        .order_by(AttemptAnswer.question_id)
    ).all()
    return QuizAttemptDetailRead(
        **QuizAttemptRead.model_validate(attempt).model_dump(),
        answers=[
            AttemptAnswerRead(
                question_id=answer.question_id,
                selected_option_id=answer.selected_option_id,
            )
            for answer in answers
        ],
    )


@router.get(
    "/attempts/{attempt_id}",
    response_model=QuizAttemptDetailRead,
    summary="Get an attempt and saved answers",
)
def get_attempt(
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizAttemptDetailRead:
    attempt = get_attempt_or_404(db, attempt_id)
    ensure_attempt_owner_or_manager(db, attempt, current_user)
    return build_attempt_detail(db, attempt)


@router.post(
    "/attempts/{attempt_id}/submit",
    response_model=QuizAttemptRead,
    summary="Submit and automatically score an attempt",
)
def submit_attempt(
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizAttemptRead:
    attempt = get_attempt_or_404(db, attempt_id)
    assessment = ensure_attempt_owner_or_manager(db, attempt, current_user)
    if current_user.role != UserRole.STUDENT.value or attempt.student_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the attempt owner can submit this attempt.",
        )
    if attempt.status != AttemptStatus.IN_PROGRESS.value:
        raise HTTPException(status_code=409, detail="This attempt has already been submitted.")

    links = db.scalars(
        select(AssessmentQuestion).where(AssessmentQuestion.assessment_id == assessment.id)
    ).all()
    question_ids = [link.question_id for link in links]
    answers = db.scalars(
        select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id)
    ).all()
    selected_by_question = {answer.question_id: answer.selected_option_id for answer in answers}
    correct_options = db.execute(
        select(QuestionOption.question_id, QuestionOption.id).where(
            QuestionOption.question_id.in_(question_ids),
            QuestionOption.is_correct.is_(True),
        )
    ).all()
    correct_by_question = {question_id: option_id for question_id, option_id in correct_options}
    attempt.question_count = len(question_ids)
    attempt.correct_count = sum(
        selected_by_question.get(question_id) is not None
        and selected_by_question.get(question_id) == correct_by_question.get(question_id)
        for question_id in question_ids
    )
    attempt.score_percent = round(attempt.correct_count * 100 / attempt.question_count, 2)
    attempt.status = AttemptStatus.SUBMITTED.value
    attempt.submitted_at = datetime.now(UTC)
    db.commit()
    db.refresh(attempt)
    return QuizAttemptRead.model_validate(attempt)
