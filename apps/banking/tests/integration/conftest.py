"""Fixtures for the account page and admin tests: accounts, operations, categories."""

from datetime import date
from decimal import Decimal

import pytest

from banking.databases.models import (
    AccountModel,
    CategoryModel,
    ImportModel,
    OperationModel,
)
from banking.domains.account import AccountType


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
    """Add an operation (to the account by default), with a category or not."""
    imports = {}

    def make(day, description="CB LABELTEST SHOP", target=account, category=None):
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
            description=description,
            amount=Decimal("-9.99"),
            occurrence=1,
            category_id=None if category is None else category.id,
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
def category_of(session):
    """The category id an operation has now, or None."""

    def get(operation):
        session.expire_all()
        return session.get(OperationModel, operation.id).category_id

    return get
