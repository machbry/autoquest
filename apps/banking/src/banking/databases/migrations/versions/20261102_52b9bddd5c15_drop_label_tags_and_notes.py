"""Drop label tags and notes: a label is a category only, to stay simple.

Revision ID: 52b9bddd5c15
Revises: 4231981d5dd6
Create Date: 2026-11-02 19:48:11.702497
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "52b9bddd5c15"
down_revision: str | None = "4231981d5dd6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the migration."""
    op.drop_column("labels", "tags", schema="banking")
    op.drop_column("labels", "note", schema="banking")


def downgrade() -> None:
    """Revert the migration; the dropped tags and notes don't come back."""
    op.add_column(
        "labels",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String(length=50)),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        schema="banking",
    )
    op.add_column(
        "labels",
        sa.Column("note", sa.String(length=500), nullable=True),
        schema="banking",
    )
