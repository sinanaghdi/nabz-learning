from datetime import date, datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.opportunities import OpportunityCategory, OpportunityStatus


class StrictInputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OpportunityCreate(StrictInputModel):
    title: str = Field(min_length=2, max_length=180)
    category: OpportunityCategory
    summary: str = Field(min_length=10, max_length=500)
    description: str = Field(min_length=20, max_length=10000)
    required_skills: str | None = Field(default=None, max_length=3000)
    application_url: str | None = Field(default=None, max_length=2048)
    deadline: date | None = None

    @field_validator("title", "summary")
    @classmethod
    def normalize_inline_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("This field cannot be blank.")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field cannot be blank.")
        return normalized

    @field_validator("required_skills")
    @classmethod
    def normalize_skills(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @field_validator("application_url")
    @classmethod
    def validate_application_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Application URL must start with http:// or https://.")
        return value


class OpportunityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    posted_by_id: int
    posted_by_name: str | None
    category: OpportunityCategory
    title: str
    summary: str
    description: str
    required_skills: str | None
    application_url: str | None
    deadline: date | None
    status: OpportunityStatus
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    is_owner: bool
