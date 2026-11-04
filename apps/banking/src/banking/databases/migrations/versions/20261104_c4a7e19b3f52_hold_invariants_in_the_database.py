"""Hold in the database the invariants only the admin enforced.

Rules on a change (never edited, no reopening) are triggers, as a CHECK can't see the
old row. They raise a named constraint, so a violation reads like any other.

Revision ID: c4a7e19b3f52
Revises: 8f3c1d2a7b90
Create Date: 2026-11-04 21:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c4a7e19b3f52"
down_revision: str | None = "8f3c1d2a7b90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WHITESPACE = (
    r"[\u0009-\u000D\u001C- \u0085   -    "
    r" 　]"
)
TRIMMED_NAME = f"name <> '' AND name !~ '^{WHITESPACE}|{WHITESPACE}$'"


def upgrade() -> None:
    """Apply the migration; it fails if a stored row breaks a rule."""
    for table in ("banks", "categories", "accounts"):
        op.create_check_constraint(
            op.f(f"ck_{table}_name_trimmed"), table, TRIMMED_NAME, schema="banking"
        )
    op.create_check_constraint(
        op.f("ck_accounts_account_number_normalized"),
        "accounts",
        "account_number ~ '^[A-Z0-9]+$'",
        schema="banking",
    )
    # Messages hold no values: Postgres errors can reach the logs.
    op.execute(
        """
        CREATE FUNCTION banking.refuse_change() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '%', TG_ARGV[1]
                USING ERRCODE = 'check_violation', CONSTRAINT = TG_ARGV[0];
        END
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER operations_bank_fields_unchanged
        BEFORE UPDATE ON banking.operations
        FOR EACH ROW WHEN (
            OLD.account_id <> NEW.account_id
            OR OLD.operation_date <> NEW.operation_date
            OR OLD.description <> NEW.description
            OR OLD.amount <> NEW.amount
        )
        EXECUTE FUNCTION banking.refuse_change(
            'ck_operations_bank_fields_unchanged',
            'An operation keeps the account, date, description and amount it has.'
        )
        """
    )
    op.execute(
        """
        CREATE TRIGGER accounts_stay_closed
        BEFORE UPDATE ON banking.accounts
        FOR EACH ROW WHEN (OLD.closed_on IS NOT NULL AND NEW.closed_on IS NULL)
        EXECUTE FUNCTION banking.refuse_change(
            'ck_accounts_stay_closed',
            'A closed account can''t be reopened.'
        )
        """
    )


def downgrade() -> None:
    """Revert the migration."""
    op.execute("DROP TRIGGER accounts_stay_closed ON banking.accounts")
    op.execute("DROP TRIGGER operations_bank_fields_unchanged ON banking.operations")
    op.execute("DROP FUNCTION banking.refuse_change()")
    op.drop_constraint(
        op.f("ck_accounts_account_number_normalized"),
        "accounts",
        type_="check",
        schema="banking",
    )
    for table in ("accounts", "categories", "banks"):
        op.drop_constraint(
            op.f(f"ck_{table}_name_trimmed"), table, type_="check", schema="banking"
        )
