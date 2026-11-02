"""Move the category onto operations: drop labels, one category per operation.

The admin edits a foreign key in place; a separate labels table can't be.

Revision ID: 8f3c1d2a7b90
Revises: e36517402419
Create Date: 2026-11-03 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8f3c1d2a7b90"
down_revision: str | None = "e36517402419"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the migration; existing labels move onto their operation."""
    op.add_column(
        "operations",
        sa.Column("category_id", sa.Integer(), nullable=True),
        schema="banking",
    )
    op.create_foreign_key(
        op.f("fk_operations_category_id"),
        "operations",
        "categories",
        ["category_id"],
        ["id"],
        source_schema="banking",
        referent_schema="banking",
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_operations_category_id"),
        "operations",
        ["category_id"],
        schema="banking",
    )
    op.execute(
        "UPDATE banking.operations AS o SET category_id = l.category_id"
        " FROM banking.labels AS l WHERE l.operation_id = o.id"
    )
    op.drop_table("labels", schema="banking")


def downgrade() -> None:
    """Revert the migration; labels come back, dated by the migration."""
    op.create_table(
        "labels",
        sa.Column("operation_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        *[
            sa.Column(
                name,
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            )
            for name in ("created_at", "updated_at")
        ],
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
    op.create_index(
        op.f("ix_labels_category_id"), "labels", ["category_id"], schema="banking"
    )
    op.execute(
        "INSERT INTO banking.labels (operation_id, category_id)"
        " SELECT id, category_id FROM banking.operations"
        " WHERE category_id IS NOT NULL"
    )
    op.drop_index(
        op.f("ix_operations_category_id"), table_name="operations", schema="banking"
    )
    op.drop_column("operations", "category_id", schema="banking")
