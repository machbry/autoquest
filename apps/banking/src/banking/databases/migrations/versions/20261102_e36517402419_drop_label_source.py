"""Drop the label source: without suggestions, every label is set by hand.

Revision ID: e36517402419
Revises: 52b9bddd5c15
Create Date: 2026-11-02 22:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e36517402419"
down_revision: str | None = "52b9bddd5c15"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the migration; Postgres drops the column's CHECK with it."""
    op.drop_column("labels", "source", schema="banking")


def downgrade() -> None:
    """Revert the migration; every label comes back as set by hand."""
    op.add_column(
        "labels",
        sa.Column(
            "source",
            sa.String(length=10),
            server_default="manual",
            nullable=False,
        ),
        schema="banking",
    )
    # The default only fills the existing rows: the app always set the source.
    op.alter_column("labels", "source", server_default=None, schema="banking")
    op.create_check_constraint(
        op.f("ck_labels_source"),
        "labels",
        "source IN ('suggestion', 'manual')",
        schema="banking",
    )
