from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import UserRole


class StrictInputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CourseCreate(StrictInputModel):
    title: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    term: str | None = Field(default=None, max_length=80)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        title = " ".join(value.split())
        if len(title) < 2:
            raise ValueError("Course title must contain at least two characters.")
        return title


class CourseUpdate(StrictInputModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    term: str | None = Field(default=None, max_length=80)
    is_active: bool | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        title = " ".join(value.split())
        if len(title) < 2:
            raise ValueError("Course title must contain at least two characters.")
        return title

    @field_validator("is_active")
    @classmethod
    def is_active_cannot_be_null(cls, value: bool | None) -> bool | None:
        if value is None:
            raise ValueError("is_active cannot be null.")
        return value


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    instructor_id: int
    title: str
    description: str | None
    term: str | None
    is_active: bool
    created_at: datetime


class CourseCreatedRead(CourseRead):
    enrollment_code: str


class EnrollmentCreate(StrictInputModel):
    enrollment_code: str = Field(min_length=6, max_length=16)

    @field_validator("enrollment_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class EnrollmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    student_id: int
    enrolled_at: datetime


class CourseStudentRead(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    enrolled_at: datetime


class TopicCreate(StrictInputModel):
    title: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int = Field(default=0, ge=0, le=10000)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        title = " ".join(value.split())
        if len(title) < 2:
            raise ValueError("Topic title must contain at least two characters.")
        return title


class TopicUpdate(StrictInputModel):
    title: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int | None = Field(default=None, ge=0, le=10000)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        title = " ".join(value.split())
        if len(title) < 2:
            raise ValueError("Topic title must contain at least two characters.")
        return title

    @field_validator("sort_order")
    @classmethod
    def sort_order_cannot_be_null(cls, value: int | None) -> int | None:
        if value is None:
            raise ValueError("sort_order cannot be null.")
        return value


class TopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: str
    description: str | None
    sort_order: int
    created_at: datetime
