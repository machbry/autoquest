"""Direct writes: the database holds the invariants, whichever component writes."""

import sys
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import insert, update
from sqlalchemy.exc import DataError, IntegrityError

from banking.databases.models import (
    AccountModel,
    BankModel,
    CategoryModel,
    OperationModel,
)
from banking.databases.repositories.base import ConstraintViolation
from banking.databases.repositories.operation_repository import OperationRepository
from banking.domains.account import AccountType

NAMED = [BankModel, CategoryModel, AccountModel]
WHITESPACE = [chr(c) for c in range(sys.maxunicode + 1) if chr(c).isspace()]


def broken(refused):
    """The name of the constraint a refused write broke."""
    return refused.value.orig.diag.constraint_name


def add_named(session, bank, model, name):
    """Insert a row of a named table, with `name`."""
    values = (
        account_values(bank, name=name) if model is AccountModel else {"name": name}
    )
    session.execute(insert(model).values(values))


def account_values(bank, **overrides):
    return {
        "name": "Direct account",
        "bank_id": bank.id,
        "type": AccountType.CURRENT,
        "opened_on": date(2020, 1, 15),
    } | overrides


def edit_operation(session, operation, **values):
    session.execute(
        update(OperationModel).where(OperationModel.id == operation.id).values(values)
    )


def set_closed_on(session, account, closed_on):
    session.execute(
        update(AccountModel)
        .where(AccountModel.id == account.id)
        .values(closed_on=closed_on)
    )


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("operation_date", date(2026, 10, 2)),
        ("description", "EDITED"),
        ("amount", Decimal("1000.00")),
    ],
)
def test_an_operations_bank_fields_cant_be_edited(
    session, add_operation, column, value
):
    operation = add_operation(date(2026, 10, 1))

    with pytest.raises(IntegrityError) as refused:
        edit_operation(session, operation, **{column: value})

    assert broken(refused) == "ck_operations_bank_fields_unchanged"


def test_an_operation_cant_move_to_another_account(session, add_operation, add_account):
    operation = add_operation(date(2026, 10, 1))
    other = add_account("Other")

    with pytest.raises(IntegrityError) as refused:
        edit_operation(session, operation, account_id=other.id)

    assert broken(refused) == "ck_operations_bank_fields_unchanged"


def test_an_operations_category_can_change(
    session, add_operation, groceries, category_of
):
    operation = add_operation(date(2026, 10, 1))

    edit_operation(session, operation, category_id=groceries.id)
    assert category_of(operation) == groceries.id

    edit_operation(session, operation, category_id=None)
    assert category_of(operation) is None


def test_a_repository_names_the_rule_a_refused_write_broke(session, add_operation):
    operation = add_operation(date(2026, 10, 1))
    copy = {
        "account_id": operation.account_id,
        "import_id": operation.import_id,
        "operation_date": operation.operation_date,
        "description": operation.description,
        "amount": operation.amount,
        "occurrence": operation.occurrence,
    }

    with pytest.raises(ConstraintViolation) as refused:
        OperationRepository(session).create(copy)

    assert refused.value.constraint == "uq_operations_occurrence"


def test_a_closed_account_cant_be_reopened(session, account):
    set_closed_on(session, account, date(2026, 3, 31))

    with pytest.raises(IntegrityError) as refused:
        set_closed_on(session, account, None)

    assert broken(refused) == "ck_accounts_stay_closed"


def test_a_closing_date_can_be_corrected(session, account):
    set_closed_on(session, account, date(2026, 3, 31))

    set_closed_on(session, account, date(2026, 4, 30))

    session.expire_all()
    assert session.get(AccountModel, account.id).closed_on == date(2026, 4, 30)


@pytest.mark.parametrize("model", NAMED)
@pytest.mark.parametrize("name", ["", " ", "   ", " x", "x ", "\tx", "x\n", "\xa0x"])
def test_a_blank_or_untrimmed_name_is_refused(session, bank, model, name):
    with pytest.raises(IntegrityError) as refused:
        add_named(session, bank, model, name)

    assert broken(refused) == f"ck_{model.__tablename__}_name_trimmed"


@pytest.mark.parametrize("char", WHITESPACE, ids=lambda char: f"U+{ord(char):04X}")
def test_every_character_the_admin_trims_is_refused_at_a_names_edges(session, char):
    # The constraint spells out this set: Postgres' own `\s` depends on the locale.
    for name in (f"{char}x", f"x{char}"):
        with pytest.raises(IntegrityError), session.begin_nested():
            session.execute(insert(BankModel).values(name=name))


@pytest.mark.parametrize("model", NAMED)
def test_a_name_with_nul_is_refused(session, bank, model):
    with pytest.raises(DataError):
        add_named(session, bank, model, "a\x00b")


@pytest.mark.parametrize("model", NAMED)
@pytest.mark.parametrize("name", ["x", "Two  words", "Épargne d'été", "A\xa0B", "a-b"])
def test_a_trimmed_name_is_stored(session, bank, model, name):
    add_named(session, bank, model, name)


@pytest.mark.parametrize(
    "number", ["", "12 345A", "12345a", "12-345", "12345A\n", "É1"]
)
def test_an_unnormalized_account_number_is_refused(session, bank, number):
    with pytest.raises(IntegrityError) as refused:
        session.execute(
            insert(AccountModel).values(account_values(bank, account_number=number))
        )

    assert broken(refused) == "ck_accounts_account_number_normalized"


def test_an_account_number_over_34_characters_is_refused(session, bank):
    with pytest.raises(DataError):
        session.execute(
            insert(AccountModel).values(account_values(bank, account_number="1" * 35))
        )


@pytest.mark.parametrize("number", [None, "12345A", "A" * 34])
def test_a_normalized_account_number_is_stored(session, bank, number):
    session.execute(
        insert(AccountModel).values(account_values(bank, account_number=number))
    )
