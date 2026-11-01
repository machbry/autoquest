from datetime import date
from decimal import Decimal

import pytest

from banking.domains.errors import InvalidError
from banking.domains.operation import OperationFields
from banking.services.imports.banque_postale_csv import FIRST_ROW_LINE, parse
from banking.tools.fakes import build_export

EXPORTED_ON = date(2026, 10, 31)


def operation(day=1, description="CB SHOP", amount="-12.34"):
    return OperationFields(date(2026, 10, day), description, Decimal(amount))


def export(*operations, **options):
    return build_export("12345A", EXPORTED_ON, operations, **options)


def replace_line(content, number, line):
    lines = content.decode("iso-8859-1").split("\r\n")
    lines[number - 1] = line
    return "\r\n".join(lines).encode("iso-8859-1")


def assert_rejected(content, message):
    with pytest.raises(InvalidError) as exc_info:
        parse(content)
    assert exc_info.value.field == "file"
    assert exc_info.value.message == message


def test_export_is_parsed():
    salary = operation(2, "VIREMENT DE ACME; SALAIRE", "2500.00")
    card = operation(5)

    parsed = parse(export(salary, card, balance=Decimal("-42.10")))

    assert parsed.account_number == "12345A"
    assert parsed.export_date == EXPORTED_ON
    assert parsed.balance == Decimal("-42.10")
    assert parsed.operations == (card, salary)  # newest first, as in the file


def test_amounts_are_exact_decimals():
    parsed = parse(export(operation(amount="0.10"), operation(amount="0.20")))

    assert sum(row.amount for row in parsed.operations) == Decimal("0.30")


def test_identical_rows_are_all_kept():
    assert len(parse(export(operation(), operation())).operations) == 2


def test_export_without_operations_is_valid():
    assert parse(export()).operations == ()


def test_non_ascii_descriptions_are_read_as_latin_1():
    parsed = parse(export(operation(description="CB CAFÉ")))

    assert parsed.operations[0].description == "CB CAFÉ"


def test_blank_trailing_lines_are_ignored():
    assert len(parse(export(operation()) + b"\r\n\r\n").operations) == 1


def test_lf_line_endings_are_accepted():
    content = export(operation()).replace(b"\r\n", b"\n")

    assert len(parse(content).operations) == 1


@pytest.mark.parametrize(
    "row",
    [
        '31/10/2026;"CB SHOP";-12.34',
        '31/10/2026;"CB SHOP";-12,3',
        '31/10/2026;"CB SHOP";+12,34',
        '31/10/2026;"CB SHOP";1 234,56',
        '31/10/2026;"CB SHOP";',
    ],
)
def test_malformed_amount_names_its_line(row):
    content = replace_line(export(operation(), operation()), FIRST_ROW_LINE + 1, row)

    assert_rejected(content, f"Line {FIRST_ROW_LINE + 1}: invalid amount.")


@pytest.mark.parametrize("value", ["2026-10-31", "31/13/2026", "1/10/2026", ""])
def test_malformed_date_names_its_line(value):
    content = replace_line(export(operation()), FIRST_ROW_LINE, f'{value};"X";-1,00')

    assert_rejected(content, f"Line {FIRST_ROW_LINE}: invalid date.")


@pytest.mark.parametrize("description", ["", "x" * 201])
def test_description_must_hold_1_to_200_characters(description):
    content = export(operation(description=description))

    assert_rejected(
        content,
        f"Line {FIRST_ROW_LINE}: the description must hold 1 to 200 characters.",
    )


@pytest.mark.parametrize("row", ['31/10/2026;"CB SHOP"', '31/10/2026;"A";"B";-1,00'])
def test_row_with_missing_or_extra_fields_names_its_line(row):
    content = replace_line(export(operation()), FIRST_ROW_LINE, row)

    assert_rejected(
        content,
        f"Line {FIRST_ROW_LINE}: expected a date, a description and an amount.",
    )


def test_export_in_another_currency_is_rejected():
    assert_rejected(export(currency="dollars"), "Only files in euros can be imported.")


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"\x89PNG\r\n\x1a\n\x00\x00",
        b"Date;Description;Amount\r\n31/10/2026;X;-1,00\r\n",
        "Numéro Compte;1\r\nType;CCP\r\n".encode("iso-8859-1"),
    ],
)
def test_unreadable_file_is_rejected(content):
    assert_rejected(content, "This file isn't a La Banque Postale CSV file.")


@pytest.mark.parametrize(
    ("number", "line"),
    [
        (2, "Kind         ;CCP"),
        (6, "not blank"),
        (7, "Date;Description;Amount"),
    ],
)
def test_unexpected_header_is_rejected(number, line):
    assert_rejected(
        replace_line(export(), number, line),
        "This file isn't a La Banque Postale CSV file.",
    )


@pytest.mark.parametrize(
    ("number", "line", "message"),
    [
        (4, "Date            ;2026-10-31", "Line 4: invalid date."),
        (5, "Solde (EUROS)   ;12.00", "Line 5: invalid amount."),
        (1, "Numéro Compte   ;", "Line 1: missing account number."),
    ],
)
def test_malformed_header_value_names_its_line(number, line, message):
    assert_rejected(replace_line(export(), number, line), message)


@pytest.mark.parametrize(
    "row",
    [
        "31/10/2026;CB\rSHOP;-1,00",  # stray carriage return in an unquoted field
        '31/10/2026;"' + "x" * 200_000 + '";-1,00',  # beyond csv's field size limit
    ],
)
def test_line_csv_cannot_read_names_its_line(row):
    # Regression: csv.Error escaped the parser, and the upload answered 500.
    content = replace_line(export(operation()), FIRST_ROW_LINE, row)

    assert_rejected(content, f"Line {FIRST_ROW_LINE}: malformed line.")


def test_account_number_is_normalized():
    content = build_export(" 123 45a ", EXPORTED_ON, [])

    assert parse(content).account_number == "12345A"


def test_nul_byte_is_rejected():
    content = replace_line(
        export(operation()), FIRST_ROW_LINE, '31/10/2026;"A\x00";-1,00'
    )

    assert_rejected(content, "This file isn't a La Banque Postale CSV file.")


def test_error_never_quotes_the_file():
    content = replace_line(export(operation()), FIRST_ROW_LINE, '31/10/2026;"SECRET";x')

    with pytest.raises(InvalidError) as exc_info:
        parse(content)
    assert "SECRET" not in exc_info.value.message
