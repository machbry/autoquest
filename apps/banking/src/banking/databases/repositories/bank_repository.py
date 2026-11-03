"""Banks, as the accounts' repository returns them; the admin creates and edits them."""

from banking.databases.models import BankModel
from banking.domains.bank import Bank


def to_bank(row: BankModel) -> Bank:
    """Convert a bank row to its domain object."""
    return Bank(id=row.id, name=row.name)
