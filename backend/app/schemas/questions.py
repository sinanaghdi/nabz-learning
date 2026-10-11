from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.course import QuestionDifficulty, QuestionStatus


class StrictInputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuestionOptionInput(StrictInputModel):
    text: str = Field(min_length=1, max_length=500)
    is_correct: bool = False

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        text = " ".join(value.split())
        if not text:
            raise ValueError("Option text cannot be blank.")
        return text


class QuestionCreate(StrictInputModel):
    topic_id: int = Field(gt=0)
    prompt: str = Field(min_length=5, max_length=10000)
    explanation: str | None = Field(default=None, max_length=5000)
    difficulty: QuestionDifficulty = QuestionDifficulty.MEDIUM
    status: QuestionStatus = QuestionStatus.DRAFT
    options: list[QuestionOptionInput] = Field(min_length=2, max_length=6)

    @field_validator("prompt")
    @classmethod
    def normalize_prompt(cls, value: str) -> str:
        prompt = value.strip()
        if len(prompt) < 5:
            raise ValueError("Question prompt must contain at least five characters.")
        return prompt

    @model_validator(mode="after")
    def exactly_one_correct_option(self) -> "QuestionCreate":
        if sum(option.is_correct for option in self.options) != 1:
            raise ValueError("A single-choice question must have exactly one correct option.")
        return self


class QuestionUpdate(StrictInputModel):
    topic_id: int | None = Field(default=None, gt=0)
    prompt: str | None = Field(default=None, min_length=5, max_length=10000)
    explanation: str | None = Field(default=None, max_length=5000)
    difficulty: QuestionDifficulty | None = None
    status: QuestionStatus | None = None
    options: list[QuestionOptionInput] | None = Field(default=None, min_length=2, max_length=6)

    @field_validator("prompt")
    @classmethod
    def normalize_prompt(cls, value: str | None) -> str | None:
        if value is None:
            return value
        prompt = value.strip()
        if len(prompt) < 5:
            raise ValueError("Question prompt must contain at least five characters.")
        return prompt

    @model_validator(mode="after")
    def validate_options_when_provided(self) -> "QuestionUpdate":
        if self.topic_id is None and "topic_id" in self.model_fields_set:
            raise ValueError("topic_id cannot be null.")
        if self.prompt is None and "prompt" in self.model_fields_set:
            raise ValueError("prompt cannot be null.")
        if self.difficulty is None and "difficulty" in self.model_fields_set:
            raise ValueError("difficulty cannot be null.")
        if self.status is None and "status" in self.model_fields_set:
            raise ValueError("status cannot be null.")
        if self.options is not None and sum(
            option.is_correct for option in self.options
        ) != 1:
            raise ValueError("A single-choice question must have exactly one correct option.")
        return self


class QuestionOptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    is_correct: bool
    position: int


class QuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    prompt: str
    explanation: str | None
    difficulty: QuestionDifficulty
    status: QuestionStatus
    created_at: datetime
    updated_at: datetime
    options: list[QuestionOptionRead]
