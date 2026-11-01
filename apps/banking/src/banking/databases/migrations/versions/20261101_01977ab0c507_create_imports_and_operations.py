"""Create imports and operations.

Revision ID: 01977ab0c507
Revises: 53dec58d5e7b
Create Date: 2026-11-01 20:12:45.146213
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "01977ab0c507"
down_revision: str | None = "53dec58d5e7b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp(name: str) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def upgrade() -> None:
    """Apply the migration."""
    op.create_table(
        "imports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("export_date", sa.Date(), nullable=False),
        sa.Column("balance", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("first_operation_on", sa.Date(), nullable=True),
        sa.Column("last_operation_on", sa.Date(), nullable=True),
        sa.Column("rows_in_file", sa.Integer(), nullable=False),
        sa.Column("rows_new", sa.Integer(), nullable=False),
        _timestamp("created_at"),
        sa.CheckConstraint(
            "last_operation_on >= first_operation_on",
            name=op.f("ck_imports_first_before_last"),
        ),
        sa.CheckConstraint(
            "rows_new BETWEEN 0 AND rows_in_file",
            name=op.f("ck_imports_rows_new_in_file"),
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["banking.accounts.id"],
            name=op.f("fk_imports_account_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_imports")),
        schema="banking",
    )
    op.create_table(
        "operations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=False),
        sa.Column("operation_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("occurrence", sa.Integer(), nullable=False),
        _timestamp("created_at"),
        _timestamp("updated_at"),
        sa.CheckConstraint(
            "occurrence >= 1", name=op.f("ck_operations_occurrence_positive")
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["banking.accounts.id"],
            name=op.f("fk_operations_account_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["import_id"],
            ["banking.imports.id"],
            name=op.f("fk_operations_import_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_operations")),
        # Also serves the account_id lookups (dedup, listing, cascade on delete).
        sa.UniqueConstraint(
            "account_id",
            "operation_date",
            "description",
            "amount",
            "occurrence",
            name="uq_operations_occurrence",
        ),
        schema="banking",
    )


def downgrade() -> None:
    """Revert the migration."""
    op.drop_table("operations", schema="banking")
    op.drop_table("imports", schema="banking")
