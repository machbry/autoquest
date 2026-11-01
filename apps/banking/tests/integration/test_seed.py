from sqlalchemy import func, select

from banking.models import Account
from banking.seed import ACCOUNTS, seed


def test_seed_creates_every_account_once(session):
    seed(session)
    count = session.scalar(select(func.count()).select_from(Account))

    assert seed(session) == 0
    assert session.scalar(select(func.count()).select_from(Account)) == count
    names = set(session.scalars(select(Account.name)))
    assert {name for name, *_ in ACCOUNTS} <= names
