"""Fake La Banque Postale CSV exports, in the real format; for the seed and the tests.

Dev only, like the seed: `fake_operations` needs Faker, which the prd image lacks.
"""

from collections.abc import Iterable
from datetime import date, timedelta
from decimal import Decimal

from faker import Faker

from banking.domains.operation import OperationFields

KINDS = ("CB", "PRLV SEPA", "VIREMENT DE", "ACHAT CB")


def build_export(
    account_number: str,
    export_date: date,
    operations: Iterable[OperationFields],
    balance: Decimal = Decimal("1234.56"),
    currency: str = "euros",
) -> bytes:
    """An export file holding these operations, newest first, as the bank writes it."""
    lines = [
        f"Numéro Compte   ;{account_number}",
        "Type         ;CCP",
        f"Compte tenu en  ;{currency}",
        f"Date            ;{export_date:%d/%m/%Y}",
        f"Solde (EUROS)   ;{_amount(balance)}",
        "",
        "Date;Libellé;Montant(EUROS)",
        *(
            f'{operation.operation_date:%d/%m/%Y};"{operation.description}";'
            f"{_amount(operation.amount)}"
            for operation in sorted(
                operations, key=lambda operation: operation.operation_date, reverse=True
            )
        ),
    ]
    return ("\r\n".join(lines) + "\r\n").encode("iso-8859-1")


def fake_operations(fake: Faker, first: date, last: date) -> list[OperationFields]:
    """Zero to five fake operations a day, from `first` to `last`."""
    operations = []
    for offset in range((last - first).days + 1):
        for _ in range(fake.random_int(0, 5)):
            kind, payee = fake.random_element(KINDS), fake.company().upper()
            operations.append(
                OperationFields(
                    operation_date=first + timedelta(days=offset),
                    description=f"{kind} {payee}",
                    amount=Decimal(fake.random_int(-15000, 5000)) / 100,
                )
            )
    return operations


def _amount(amount: Decimal) -> str:
    return f"{amount:.2f}".replace(".", ",")
