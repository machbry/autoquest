"""Create categories and labels.

Revision ID: 4231981d5dd6
Revises: 01977ab0c507
Create Date: 2026-11-02 11:37:24.922614
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "4231981d5dd6"
down_revision: str | None = "01977ab0c507"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            name,
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        )
        for name in ("created_at", "updated_at")
    ]


def upgrade() -> None:
    """Apply the migration."""
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("name", name=op.f("uq_categories_name")),
        schema="banking",
    )
    op.create_table(
        "labels",
        sa.Column("operation_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String(length=50)),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("source", sa.String(length=10), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "source IN ('suggestion', 'manual')", name=op.f("ck_labels_source")
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["banking.categories.id"],
            name=op.f("fk_labels_category_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["banking.operations.id"],
            name=op.f("fk_labels_operation_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("operation_id", name=op.f("pk_labels")),
        schema="banking",
    )
    # Serves the foreign key checks on category delete and merge.
    op.create_index(
        op.f("ix_labels_category_id"), "labels", ["category_id"], schema="banking"
    )


def downgrade() -> None:
    """Revert the migration."""
    op.drop_table("labels", schema="banking")
    op.drop_table("categories", schema="banking")
