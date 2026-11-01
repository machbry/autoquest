from sqlalchemy import func, select

from banking.models import Account, Bank
from banking.seed import ACCOUNTS, BANKS, seed


def count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def test_seed_creates_every_bank_and_account_once(session):
    seed(session)
    banks, accounts = count(session, Bank), count(session, Account)

    assert seed(session) == 0
    assert (count(session, Bank), count(session, Account)) == (banks, accounts)
    assert set(BANKS) <= set(session.scalars(select(Bank.name)))
    assert {name for name, *_ in ACCOUNTS} <= set(session.scalars(select(Account.name)))
