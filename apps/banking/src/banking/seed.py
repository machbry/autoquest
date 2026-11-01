"""Deterministic fake data for the local stack: `python -m banking.seed`.

Dev only: Faker comes from the dev dependency group, which the prd image doesn't
install. It writes through the services, like the app. Re-running it adds nothing.
"""

import logging
from datetime import date

from faker import Faker
from sqlalchemy.orm import Session

from banking.databases.engine import get_engine
from banking.databases.models import AccountType
from banking.services.accounts.account_service import AccountFields, AccountService
from banking.services.banks.bank_service import BankService

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


def seed(session: Session) -> int:
    """Add the fake banks and accounts missing (by name); return how many were added."""
    bank_service, account_service = BankService(session), AccountService(session)
    banks = {bank.name: bank.id for bank in bank_service.list()}
    existing = {account.name for account in account_service.list()}
    added = 0
    for name in BANKS:
        if name not in banks:
            banks[name] = bank_service.add(name).id
            added += 1

    fake = Faker()
    fake.seed_instance(SEED)
    for name, bank, type_, closed in ACCOUNTS:
        # Drawn for every account, even skipped ones, so values stay the same.
        opened_on = fake.date_between(*OPENED_BETWEEN)
        closed_on = fake.date_between(opened_on, CLOSED_BEFORE) if closed else None
        number = fake.bothify("##########?", letters="ABCDEFGHJK")
        if name in existing:
            continue
        fields = AccountFields(
            name=name,
            bank_id=banks[bank],
            type=type_,
            account_number=None if bank == NO_ACCOUNT_NUMBER else number,
            opened_on=opened_on,
        )
        account = account_service.create(fields)
        if closed_on:
            account_service.close(account.id, closed_on)
        added += 1
    return added


def main() -> None:
    """Seed the database at `BANKING_DB_URL`."""
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    with Session(get_engine()) as session:
        logger.info("%d banks and accounts added", seed(session))


if __name__ == "__main__":
    main()
