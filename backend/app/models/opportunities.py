from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.user import User

from app.db.base import Base


class OpportunityCategory(StrEnum):
    JOB = "job"
    INTERNSHIP = "internship"
    RESEARCH = "research"
    PROJECT = "project"
    PAPER = "paper"


class OpportunityStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class Opportunity(Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        CheckConstraint(
            "category IN ('job', 'internship', 'research', 'project', 'paper')",
            name="ck_opportunities_category",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'closed')",
            name="ck_opportunities_status",
        ),
        CheckConstraint("length(title) >= 2", name="ck_opportunities_title_length"),
        CheckConstraint("length(summary) >= 10", name="ck_opportunities_summary_length"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    posted_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=OpportunityStatus.DRAFT.value,
        server_default=OpportunityStatus.DRAFT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[User] = relationship("User", lazy="joined")
