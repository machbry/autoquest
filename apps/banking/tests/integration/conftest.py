"""Fixtures for the label and operations table tests: operations, categories, labels."""

from datetime import date
from decimal import Decimal

import pytest

from banking.databases.models import (
    AccountModel,
    CategoryModel,
    ImportModel,
    LabelModel,
    OperationModel,
)
from banking.domains.account import AccountType
from banking.domains.label import LabelSource

# Descriptions by name, with payees no seed operation uses: the seed's labels must
# not suggest anything here. "novel" is never labelled by any test.
DESCRIPTIONS = {
    "shop": "ACHAT CB LABELTEST SHOP {:%d.%m.%y} CARTE NUMERO 195",
    "other": "PRLV SEPA LABELTEST OTHER {:%d%m}",
    "novel": "VIR LABELTEST NOBODY BEFORE {:%d%m}",
}


@pytest.fixture
def add_account(session, bank):
    """Add an account to a bank (the test bank by default); return it."""

    def make(name="Label account", target_bank=bank):
        account = AccountModel(
            name=name,
            bank=target_bank,
            type=AccountType.CURRENT,
            opened_on=date(2020, 1, 15),
        )
        session.add(account)
        session.commit()
        return account

    return make


@pytest.fixture
def account(add_account):
    return add_account()


@pytest.fixture
def add_operation(session, account):
    """Add an operation (to the account by default); return it.

    The description is a name from DESCRIPTIONS or a template, formatted with the day.
    """
    imports = {}

    def make(day, description="shop", target=account, amount="-9.99"):
        if target.id not in imports:
            imports[target.id] = ImportModel(
                account_id=target.id,
                export_date=date(2026, 11, 2),
                balance=Decimal("100.00"),
                rows_in_file=0,
                rows_new=0,
            )
            session.add(imports[target.id])
            session.flush()
        operation = OperationModel(
            account_id=target.id,
            import_id=imports[target.id].id,
            operation_date=day,
            description=DESCRIPTIONS.get(description, description).format(day),
            amount=Decimal(amount),
            occurrence=1,
        )
        session.add(operation)
        session.commit()
        return operation

    return make


@pytest.fixture
def add_category(session):
    """Add a category; return it."""

    def make(name):
        category = CategoryModel(name=name)
        session.add(category)
        session.commit()
        return category

    return make


@pytest.fixture
def groceries(add_category):
    return add_category("Test groceries")


@pytest.fixture
def leisure(add_category):
    return add_category("Test leisure")


@pytest.fixture
def add_label(session):
    """Label an operation; return the label."""

    def make(operation, category, source=LabelSource.MANUAL):
        label = LabelModel(
            operation_id=operation.id, category_id=category.id, source=source
        )
        session.add(label)
        session.commit()
        return label

    return make


@pytest.fixture
def stored(session):
    """The label of an operation as stored now, or None."""

    def get(operation):
        session.expire_all()
        return session.get(LabelModel, operation.id)

    return get
