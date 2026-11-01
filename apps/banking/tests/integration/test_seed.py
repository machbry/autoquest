from sqlalchemy import func, select

from banking.databases.models import AccountModel, BankModel
from banking.seed import ACCOUNTS, BANKS, seed


def count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def test_seed_creates_every_bank_and_account_once(session):
    seed(session)
    banks, accounts = count(session, BankModel), count(session, AccountModel)

    assert seed(session) == 0
    assert (count(session, BankModel), count(session, AccountModel)) == (
        banks,
        accounts,
    )
    assert set(BANKS) <= set(session.scalars(select(BankModel.name)))
    assert {name for name, *_ in ACCOUNTS} <= set(
        session.scalars(select(AccountModel.name))
    )
