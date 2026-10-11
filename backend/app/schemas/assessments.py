from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.assessments import AssessmentStatus, AttemptStatus


class StrictInputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AssessmentCreate(StrictInputModel):
    title: str = Field(min_length=2, max_length=180)
    instructions: str | None = Field(default=None, max_length=4000)
    question_ids: list[int] = Field(min_length=1, max_length=100)
    duration_minutes: int | None = Field(default=None, ge=1, le=300)
    max_attempts: int = Field(default=1, ge=1, le=10)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Assessment title must contain at least two characters.")
        return normalized

    @model_validator(mode="after")
    def unique_question_ids(self) -> "AssessmentCreate":
        if len(self.question_ids) != len(set(self.question_ids)):
            raise ValueError("question_ids must not contain duplicates.")
        if any(question_id <= 0 for question_id in self.question_ids):
            raise ValueError("Question IDs must be positive.")
        return self


class AssessmentUpdate(StrictInputModel):
    title: str | None = Field(default=None, min_length=2, max_length=180)
    instructions: str | None = Field(default=None, max_length=4000)
    question_ids: list[int] | None = Field(default=None, min_length=1, max_length=100)
    duration_minutes: int | None = Field(default=None, ge=1, le=300)
    max_attempts: int | None = Field(default=None, ge=1, le=10)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Assessment title must contain at least two characters.")
        return normalized

    @model_validator(mode="after")
    def validate_nullable_fields_and_questions(self) -> "AssessmentUpdate":
        for field in ("title", "duration_minutes", "max_attempts", "question_ids"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        if self.question_ids is not None:
            if len(self.question_ids) != len(set(self.question_ids)):
                raise ValueError("question_ids must not contain duplicates.")
            if any(question_id <= 0 for question_id in self.question_ids):
                raise ValueError("Question IDs must be positive.")
        return self


class AnswerSubmission(StrictInputModel):
    selected_option_id: int = Field(gt=0)


class AssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: str
    instructions: str | None
    status: AssessmentStatus
    duration_minutes: int | None
    max_attempts: int
    question_count: int
    created_at: datetime
    published_at: datetime | None


class StudentOptionRead(BaseModel):
    id: int
    text: str
    position: int


class StudentQuestionRead(BaseModel):
    id: int
    prompt: str
    options: list[StudentOptionRead]


class AssessmentDetailRead(AssessmentRead):
    questions: list[StudentQuestionRead]


class QuizAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assessment_id: int
    student_id: int
    attempt_number: int
    status: AttemptStatus
    question_count: int
    correct_count: int | None
    score_percent: float | None
    started_at: datetime
    submitted_at: datetime | None


class AttemptAnswerRead(BaseModel):
    question_id: int
    selected_option_id: int


class QuizAttemptDetailRead(QuizAttemptRead):
    answers: list[AttemptAnswerRead]
