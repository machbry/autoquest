"""Deterministic fake data for the local stack: `python -m banking.seed`.

Dev only: Faker comes from the dev dependency group, which the prd image doesn't
install. Re-running it adds nothing.
"""

import logging
from datetime import date

from faker import Faker
from sqlalchemy import select
from sqlalchemy.orm import Session

from banking.db import get_engine
from banking.models import Account, AccountType, Bank

logger = logging.getLogger(__name__)

SEED = 42
# Fixed bounds, so the generated dates don't depend on the day the seed runs.
OPENED_BETWEEN = (date(2015, 1, 1), date(2024, 12, 31))
CLOSED_BEFORE = date(2026, 6, 30)
ACCOUNTS = [
    # name, bank, type, closed
    ("Current account", Bank.BANQUE_POSTALE, AccountType.CURRENT, False),
    ("Livret A", Bank.BANQUE_POSTALE, AccountType.SAVINGS, False),
    ("Old savings", Bank.BANQUE_POSTALE, AccountType.SAVINGS, True),
    ("CFCAL savings", Bank.CFCAL, AccountType.SAVINGS, False),
    ("PEA", Bank.FORTUNEO, AccountType.PEA, False),
    ("Life insurance", Bank.GOODVEST, AccountType.LIFE_INSURANCE, False),
]


def fake_accounts(fake: Faker) -> list[Account]:
    """One account per kind, one of them closed; Goodvest has no account number."""
    accounts = []
    for name, bank, type_, closed in ACCOUNTS:
        opened_on = fake.date_between(*OPENED_BETWEEN)
        closed_on = fake.date_between(opened_on, CLOSED_BEFORE) if closed else None
        # Drawn even when unused, so each account's values don't depend on the others.
        number = fake.bothify("##########?", letters="ABCDEFGHJK")
        accounts.append(
            Account(
                name=name,
                bank=bank,
                type=type_,
                account_number=None if bank is Bank.GOODVEST else number,
                opened_on=opened_on,
                closed_on=closed_on,
            )
        )
    return accounts


def seed(session: Session) -> int:
    """Add the fake accounts that don't exist yet (by name); return how many."""
    fake = Faker()
    fake.seed_instance(SEED)
    existing = set(session.scalars(select(Account.name)))
    new = [account for account in fake_accounts(fake) if account.name not in existing]
    session.add_all(new)
    session.commit()
    return len(new)


def main() -> None:
    """Seed the database at `BANKING_DB_URL`."""
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    with Session(get_engine()) as session:
        logger.info("%d accounts added", seed(session))


if __name__ == "__main__":
    main()
