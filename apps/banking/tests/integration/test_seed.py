from sqlalchemy import func, select

from banking.databases.models import (
    AccountModel,
    BankModel,
    CategoryModel,
    ImportModel,
    OperationModel,
)
from banking.tools.seed import (
    ACCOUNTS,
    BANKS,
    CATEGORIES,
    EXPORT_DATES,
    IMPORTED_ACCOUNT,
    seed,
)

MODELS = (BankModel, AccountModel, ImportModel, OperationModel, CategoryModel)


def count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def test_seed_creates_every_bank_account_import_and_category_once(session):
    seed(session)
    counts = [count(session, model) for model in MODELS]

    assert seed(session) == 0
    assert [count(session, model) for model in MODELS] == counts
    export_dates = session.scalars(
        select(ImportModel.export_date)
        .join(AccountModel, AccountModel.id == ImportModel.account_id)
        .where(AccountModel.name == IMPORTED_ACCOUNT)
    )
    assert set(export_dates) == set(EXPORT_DATES)
    assert set(BANKS) <= set(session.scalars(select(BankModel.name)))
    assert {name for name, *_ in ACCOUNTS} <= set(
        session.scalars(select(AccountModel.name))
    )
    assert set(CATEGORIES) <= set(session.scalars(select(CategoryModel.name)))
