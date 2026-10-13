"""Create moderated academic and industry opportunities.

Revision ID: 20261013_0004
Revises: 20261011_0003
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261013_0004"
down_revision: str | None = "20261011_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "opportunities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "posted_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("required_skills", sa.Text(), nullable=True),
        sa.Column("application_url", sa.String(length=2048), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "category IN ('job', 'internship', 'research', 'project', 'paper')",
            name="ck_opportunities_category",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'closed')",
            name="ck_opportunities_status",
        ),
        sa.CheckConstraint("length(title) >= 2", name="ck_opportunities_title_length"),
        sa.CheckConstraint("length(summary) >= 10", name="ck_opportunities_summary_length"),
    )
    op.create_index("ix_opportunities_posted_by_id", "opportunities", ["posted_by_id"])
    op.create_index("ix_opportunities_status_category", "opportunities", ["status", "category"])


def downgrade() -> None:
    op.drop_index("ix_opportunities_status_category", table_name="opportunities")
    op.drop_index("ix_opportunities_posted_by_id", table_name="opportunities")
    op.drop_table("opportunities")
