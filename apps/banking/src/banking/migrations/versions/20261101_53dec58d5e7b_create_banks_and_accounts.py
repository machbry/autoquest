"""Create banks and accounts.

Revision ID: 53dec58d5e7b
Revises:
Create Date: 2026-11-01 18:19:00.061644
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "53dec58d5e7b"
down_revision: str | None = None
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
        "banks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_banks")),
        sa.UniqueConstraint("name", name=op.f("uq_banks_name")),
        schema="banking",
    )
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=14), nullable=False),
        sa.Column("account_number", sa.String(length=34), nullable=True),
        sa.Column("opened_on", sa.Date(), nullable=False),
        sa.Column("closed_on", sa.Date(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "type IN ('current', 'savings', 'pea', 'life_insurance')",
            name=op.f("ck_accounts_type"),
        ),
        sa.CheckConstraint(
            "closed_on >= opened_on", name=op.f("ck_accounts_closed_after_opened")
        ),
        sa.ForeignKeyConstraint(
            ["bank_id"],
            ["banking.banks.id"],
            name=op.f("fk_accounts_bank_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accounts")),
        sa.UniqueConstraint("account_number", name=op.f("uq_accounts_account_number")),
        sa.UniqueConstraint("name", name=op.f("uq_accounts_name")),
        schema="banking",
    )


def downgrade() -> None:
    """Revert the migration."""
    op.drop_table("accounts", schema="banking")
    op.drop_table("banks", schema="banking")
