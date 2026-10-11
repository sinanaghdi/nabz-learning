from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.course_access import ensure_course_manager, get_course_or_404
from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.course import (
    CourseTopic,
    Question,
    QuestionDifficulty,
    QuestionOption,
    QuestionStatus,
)
from app.models.user import User, UserRole
from app.schemas.questions import QuestionCreate, QuestionRead, QuestionUpdate

router = APIRouter(tags=["question bank"])


def require_course_question_manager(db: Session, course_id: int, user: User) -> None:
    course = get_course_or_404(db, course_id)
    ensure_course_manager(course, user)


def get_question_or_404(db: Session, course_id: int, question_id: int) -> Question:
    question = db.scalar(
        select(Question)
        .join(CourseTopic, Question.topic_id == CourseTopic.id)
        .where(Question.id == question_id, CourseTopic.course_id == course_id)
        .options(selectinload(Question.options))
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found in this course.")
    return question


def ensure_topic_belongs_to_course(db: Session, course_id: int, topic_id: int) -> None:
    topic_id_found = db.scalar(
        select(CourseTopic.id).where(
            CourseTopic.id == topic_id,
            CourseTopic.course_id == course_id,
        )
    )
    if topic_id_found is None:
        raise HTTPException(
            status_code=422,
            detail="The selected topic does not belong to this course.",
        )


def ensure_question_manager(user: User) -> None:
    if user.role not in {UserRole.INSTRUCTOR.value, UserRole.ADMIN.value}:
        raise HTTPException(
            status_code=403,
            detail="Only instructors and administrators can access the question bank.",
        )


@router.post(
    "/courses/{course_id}/questions",
    response_model=QuestionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a single-choice question to the bank",
)
def create_question(
    course_id: int,
    payload: QuestionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuestionRead:
    require_course_question_manager(db, course_id, current_user)
    ensure_question_manager(current_user)
    ensure_topic_belongs_to_course(db, course_id, payload.topic_id)

    question = Question(
        topic_id=payload.topic_id,
        prompt=payload.prompt.strip(),
        explanation=payload.explanation,
        difficulty=payload.difficulty.value,
        status=payload.status.value,
        options=[
            QuestionOption(text=option.text.strip(), is_correct=option.is_correct, position=index)
            for index, option in enumerate(payload.options)
        ],
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return QuestionRead.model_validate(question)


@router.get(
    "/courses/{course_id}/questions",
    response_model=list[QuestionRead],
    summary="List questions in a course bank",
)
def list_questions(
    course_id: int,
    topic_id: int | None = Query(default=None, gt=0),
    difficulty: QuestionDifficulty | None = None,
    question_status: QuestionStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[QuestionRead]:
    require_course_question_manager(db, course_id, current_user)
    ensure_question_manager(current_user)
    statement = (
        select(Question)
        .join(CourseTopic, Question.topic_id == CourseTopic.id)
        .where(CourseTopic.course_id == course_id)
        .options(selectinload(Question.options))
    )
    if topic_id is not None:
        statement = statement.where(Question.topic_id == topic_id)
    if difficulty is not None:
        statement = statement.where(Question.difficulty == difficulty.value)
    if question_status is not None:
        statement = statement.where(Question.status == question_status.value)
    questions = db.scalars(statement.order_by(Question.created_at.desc())).all()
    return [QuestionRead.model_validate(question) for question in questions]


@router.get(
    "/courses/{course_id}/questions/{question_id}",
    response_model=QuestionRead,
    summary="Get a question from the bank",
)
def get_question(
    course_id: int,
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuestionRead:
    require_course_question_manager(db, course_id, current_user)
    ensure_question_manager(current_user)
    question = get_question_or_404(db, course_id, question_id)
    return QuestionRead.model_validate(question)


@router.patch(
    "/courses/{course_id}/questions/{question_id}",
    response_model=QuestionRead,
    summary="Update a question",
)
def update_question(
    course_id: int,
    question_id: int,
    payload: QuestionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuestionRead:
    require_course_question_manager(db, course_id, current_user)
    ensure_question_manager(current_user)
    question = get_question_or_404(db, course_id, question_id)
    changes = payload.model_dump(exclude_unset=True)
    new_options = changes.pop("options", None)

    if "topic_id" in changes and changes["topic_id"] is not None:
        ensure_topic_belongs_to_course(db, course_id, changes["topic_id"])
    for field, value in changes.items():
        if field == "prompt" and value is not None:
            value = value.strip()
        if field in {"difficulty", "status"} and value is not None:
            value = value.value
        setattr(question, field, value)

    if new_options is not None:
        question.options = [
            QuestionOption(text=option.text.strip(), is_correct=option.is_correct, position=index)
            for index, option in enumerate(new_options)
        ]

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The question could not be saved because of a data conflict.",
        ) from None
    db.refresh(question)
    return QuestionRead.model_validate(question)


@router.delete(
    "/courses/{course_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a question",
)
def delete_question(
    course_id: int,
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    require_course_question_manager(db, course_id, current_user)
    ensure_question_manager(current_user)
    question = get_question_or_404(db, course_id, question_id)
    db.delete(question)
    db.commit()
    return None
