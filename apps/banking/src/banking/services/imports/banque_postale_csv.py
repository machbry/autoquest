"""Parser of La Banque Postale CSV exports: bytes in, parsed export out, no I/O.

The format, observed on a real export: ISO-8859-1, CRLF, five `label;value` header
lines with space-padded labels (account number, account type, currency, export date,
balance), a blank line, the `Date;Libellé;Montant(EUROS)` column header, then one
`dd/mm/yyyy;"description";-12,34` row per operation, newest first. Amounts use a
decimal comma, no `+` and no thousands separator.

Errors name the line at fault, never its content: it is personal financial data.
"""

import csv
import re
from contextlib import suppress
from datetime import date, datetime
from decimal import Decimal

from banking.domains.account import normalize_account_number
from banking.domains.errors import InvalidError
from banking.domains.import_ import Export
from banking.domains.operation import OperationFields

ENCODING = "iso-8859-1"
HEADER_LABELS = ("Numéro Compte", "Type", "Compte tenu en", "Date", "Solde (EUROS)")
COLUMNS = "Date;Libellé;Montant(EUROS)"
# Header lines, the blank line, then the column header.
FIRST_ROW_LINE = len(HEADER_LABELS) + 3
CURRENCY = "euros"
NOT_AN_EXPORT = "This file isn't a Banque Postale CSV export."
MAX_DESCRIPTION = 200
# At most 10 integer digits: amounts are NUMERIC(12, 2).
AMOUNT = re.compile(r"-?\d{1,10},\d{2}")
BALANCE = re.compile(r"[-+]?\d{1,10},\d{2}")
DATE = re.compile(r"\d{2}/\d{2}/\d{4}")
# Not str.splitlines(): it also splits on characters (U+0085…) a description may hold.
LINE_BREAK = re.compile(r"\r?\n")


def parse(content: bytes) -> Export:
    """Parse an export file.

    Raises:
        InvalidError: the file isn't a Banque Postale CSV export in euros, or a line is
            malformed (the message gives its number).
    """
    text = content.decode(ENCODING)  # Never fails: every byte is a character.
    # Postgres text can't hold NUL, and no export contains one.
    if "\x00" in text:
        raise _invalid(NOT_AN_EXPORT)
    lines = LINE_BREAK.split(text)
    account_number, export_date, balance = _header(lines)
    operations = tuple(
        _operation(line, number)
        for number, line in enumerate(lines[FIRST_ROW_LINE - 1 :], FIRST_ROW_LINE)
        if line.strip()
    )
    return Export(account_number, export_date, balance, operations)


def _header(lines: list[str]) -> tuple[str, date, Decimal]:
    """Account number (normalized), export date and balance, from the first lines."""
    fields = [line.split(";") for line in lines[: len(HEADER_LABELS)]]
    separator = [
        line.strip() for line in lines[len(HEADER_LABELS) : FIRST_ROW_LINE - 1]
    ]
    if (
        any(len(field) != 2 for field in fields)
        or [field[0].strip() for field in fields] != list(HEADER_LABELS)
        or separator != ["", COLUMNS]
    ):
        raise _invalid(NOT_AN_EXPORT)

    account_number, _type, currency, export_date, balance = (
        field[1].strip() for field in fields
    )
    if currency != CURRENCY:
        raise _invalid("Only exports in euros can be imported.")
    if not account_number:
        raise _invalid("Line 1: missing account number.")
    return (
        normalize_account_number(account_number),
        _date(export_date, 4),
        _amount(balance, BALANCE, 5),
    )


def _operation(line: str, number: int) -> OperationFields:
    """One row: date, description and amount."""
    try:
        fields = next(csv.reader([line], delimiter=";"))
    except csv.Error:  # A stray carriage return, or a field over csv's size limit.
        raise _invalid(f"Line {number}: malformed line.") from None
    if len(fields) != 3:
        raise _invalid(f"Line {number}: expected a date, a description and an amount.")
    operation_date, description, amount = fields
    if not description or len(description) > MAX_DESCRIPTION:
        raise _invalid(
            f"Line {number}: the description must hold 1 to {MAX_DESCRIPTION} "
            "characters."
        )
    return OperationFields(
        operation_date=_date(operation_date, number),
        description=description,
        amount=_amount(amount, AMOUNT, number),
    )


def _date(value: str, number: int) -> date:
    """A `dd/mm/yyyy` date."""
    if DATE.fullmatch(value):
        with suppress(ValueError):  # A day or month out of range.
            return datetime.strptime(value, "%d/%m/%Y").date()
    raise _invalid(f"Line {number}: invalid date.")


def _amount(value: str, pattern: re.Pattern[str], number: int) -> Decimal:
    """An amount with a decimal comma, exact to the cent."""
    if not pattern.fullmatch(value):
        raise _invalid(f"Line {number}: invalid amount.")
    return Decimal(value.replace(",", "."))


def _invalid(message: str) -> InvalidError:
    return InvalidError("file", message)
