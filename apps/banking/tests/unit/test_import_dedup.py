from datetime import date
from decimal import Decimal

from banking.domains.operation import OperationFields
from banking.services.imports.import_service import new_occurrences

COFFEE = OperationFields(date(2026, 10, 1), "CB CAFE", Decimal("-2.50"))
RENT = OperationFields(date(2026, 10, 1), "PRLV LOYER", Decimal("-700.00"))


def test_every_operation_is_new_for_an_empty_account():
    assert new_occurrences([COFFEE, RENT], {}) == [(COFFEE, 1), (RENT, 1)]


def test_identical_operations_get_successive_occurrences():
    assert new_occurrences([COFFEE, COFFEE], {}) == [(COFFEE, 1), (COFFEE, 2)]


def test_known_operations_are_skipped():
    assert new_occurrences([COFFEE, RENT], {COFFEE: 1, RENT: 1}) == []


def test_only_copies_beyond_the_known_count_are_new():
    assert new_occurrences([COFFEE] * 3, {COFFEE: 1}) == [(COFFEE, 2), (COFFEE, 3)]


def test_fewer_copies_than_known_add_nothing():
    # An older, shorter export: the stored copies stay.
    assert new_occurrences([COFFEE], {COFFEE: 2}) == []


def test_same_text_on_another_day_or_amount_is_another_operation():
    other_day = OperationFields(date(2026, 10, 2), "CB CAFE", Decimal("-2.50"))
    other_amount = OperationFields(date(2026, 10, 1), "CB CAFE", Decimal("-2.60"))

    assert new_occurrences([other_day, other_amount], {COFFEE: 1}) == [
        (other_day, 1),
        (other_amount, 1),
    ]


def test_amounts_compare_by_value():
    # Postgres returns NUMERIC(12, 2) values with two decimals, the parser may not.
    known = {OperationFields(date(2026, 10, 1), "CB CAFE", Decimal("-2.5")): 1}

    assert new_occurrences([COFFEE], known) == []
