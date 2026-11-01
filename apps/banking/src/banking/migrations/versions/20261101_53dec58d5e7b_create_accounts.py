"""Create accounts.

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


def upgrade() -> None:
    """Apply the migration."""
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("bank", sa.String(length=14), nullable=False),
        sa.Column("type", sa.String(length=14), nullable=False),
        sa.Column("account_number", sa.String(length=34), nullable=True),
        sa.Column("opened_on", sa.Date(), nullable=False),
        sa.Column("closed_on", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "bank IN ('banque_postale', 'cfcal', 'fortuneo', 'goodvest')",
            name=op.f("ck_accounts_bank"),
        ),
        sa.CheckConstraint(
            "type IN ('current', 'savings', 'pea', 'life_insurance')",
            name=op.f("ck_accounts_type"),
        ),
        sa.CheckConstraint(
            "closed_on >= opened_on", name=op.f("ck_accounts_closed_after_opened")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accounts")),
        sa.UniqueConstraint("account_number", name=op.f("uq_accounts_account_number")),
        sa.UniqueConstraint("name", name=op.f("uq_accounts_name")),
        schema="banking",
    )


def downgrade() -> None:
    """Revert the migration."""
    op.drop_table("accounts", schema="banking")
