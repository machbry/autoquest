from sqlalchemy import func, select

from banking.databases.models import (
    AccountModel,
    BankModel,
    CategoryModel,
    ImportModel,
    LabelModel,
    OperationModel,
)
from banking.tools.seed import (
    ACCOUNTS,
    BANKS,
    CATEGORIES,
    EXPORT_DATES,
    IMPORTED_ACCOUNT,
    PAYEE_LABELS,
    seed,
)

MODELS = (
    BankModel,
    AccountModel,
    ImportModel,
    OperationModel,
    CategoryModel,
    LabelModel,
)


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


def test_seed_labels_the_first_export_only(session):
    seed(session)

    rows = session.execute(
        select(
            OperationModel.operation_date, OperationModel.description, LabelModel.source
        )
        .join(AccountModel, AccountModel.id == OperationModel.account_id)
        .outerjoin(LabelModel, LabelModel.operation_id == OperationModel.id)
        .where(AccountModel.name == IMPORTED_ACCOUNT)
    ).all()

    # A database seeded before the payee pool existed keeps its operations unlabelled.
    seeded = [row for row in rows if any(payee in row[1] for payee in PAYEE_LABELS)]
    first_export = [row for row in seeded if row[0] <= EXPORT_DATES[0]]
    assert all(source is not None for *_, source in first_export)
    assert all(source is None for day, _, source in seeded if day > EXPORT_DATES[0])
