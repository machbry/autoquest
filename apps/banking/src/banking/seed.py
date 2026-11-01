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
NO_ACCOUNT_NUMBER = "Goodvest"
BANKS = ["La Banque Postale", "CFCAL", "Fortuneo", NO_ACCOUNT_NUMBER]
ACCOUNTS = [
    # name, bank, type, closed
    ("Current account", "La Banque Postale", AccountType.CURRENT, False),
    ("Livret A", "La Banque Postale", AccountType.SAVINGS, False),
    ("Old savings", "La Banque Postale", AccountType.SAVINGS, True),
    ("CFCAL savings", "CFCAL", AccountType.SAVINGS, False),
    ("PEA", "Fortuneo", AccountType.PEA, False),
    ("Life insurance", NO_ACCOUNT_NUMBER, AccountType.LIFE_INSURANCE, False),
]


def fake_accounts(fake: Faker, banks: dict[str, Bank]) -> list[Account]:
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
                bank=banks[bank],
                type=type_,
                account_number=None if bank == NO_ACCOUNT_NUMBER else number,
                opened_on=opened_on,
                closed_on=closed_on,
            )
        )
    return accounts


def seed(session: Session) -> int:
    """Add the fake banks and accounts missing (by name); return how many were added."""
    banks = {bank.name: bank for bank in session.scalars(select(Bank))}
    new_banks = [Bank(name=name) for name in BANKS if name not in banks]
    banks |= {bank.name: bank for bank in new_banks}
    fake = Faker()
    fake.seed_instance(SEED)
    existing = set(session.scalars(select(Account.name)))
    new_accounts = [
        account
        for account in fake_accounts(fake, banks)
        if account.name not in existing
    ]
    session.add_all([*new_banks, *new_accounts])
    session.commit()
    return len(new_banks) + len(new_accounts)


def main() -> None:
    """Seed the database at `BANKING_DB_URL`."""
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    with Session(get_engine()) as session:
        logger.info("%d banks and accounts added", seed(session))


if __name__ == "__main__":
    main()
