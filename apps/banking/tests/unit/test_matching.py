from datetime import date
from decimal import Decimal

import pytest

from banking.domains.label import LabelFields, LabelSource, PastLabel, Suggestion
from banking.domains.operation import Operation
from banking.services.labels.matching import (
    latest_by_key,
    match_key,
    similar_ids,
    source_of,
    suggest,
)


def past(operation_id, day, description, category_id=1):
    return PastLabel(operation_id, day, description, category_id)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        # The acceptance criterion: card date and card number differ.
        (
            "ACHAT CB SHOP 28.10.26 CARTE NUMERO 195",
            "ACHAT CB SHOP 02.11.26 CARTE NUMERO 195",
        ),
        ("PRLV SEPA ENERGIE REF 2026103112", "PRLV SEPA ENERGIE REF 2026113045"),
        ("CB  SHOP   12.10.26", "cb shop 13.10.26"),
        ("VIREMENT DE EMPLOYEUR", "VIREMENT DE EMPLOYEUR"),
    ],
)
def test_same_operation_with_different_noise_matches(a, b):
    assert match_key(a) == match_key(b)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("ACHAT CB SHOP 28.10.26", "ACHAT CB OTHER SHOP 28.10.26"),
        ("PRLV SEPA ENERGIE", "PRLV SEPA TELECOM"),
        ("CB SHOP", "VIREMENT DE SHOP"),
    ],
)
def test_different_payees_do_not_match(a, b):
    assert match_key(a) != match_key(b)


def test_key_drops_only_words_with_digits():
    assert (
        match_key("ACHAT CB SHOP 28.10.26 CARTE NUMERO 195")
        == "ACHAT CB SHOP CARTE NUMERO"
    )


def test_latest_matching_label_is_suggested():
    history = [
        past(1, date(2026, 9, 1), "CB SHOP 01.09.26", category_id=1),
        past(3, date(2026, 10, 1), "CB SHOP 01.10.26", category_id=2),
        past(2, date(2026, 10, 1), "CB SHOP 01.10.26", category_id=3),
        past(4, date(2026, 10, 20), "CB OTHER 20.10.26", category_id=4),
    ]

    assert suggest(history, "CB SHOP 02.11.26") == Suggestion(2, date(2026, 10, 1))


def test_no_matching_history_suggests_nothing():
    history = [past(1, date(2026, 9, 1), "CB SHOP 01.09.26")]

    assert suggest(history, "CB OTHER 02.11.26") is None
    assert suggest([], "CB SHOP 02.11.26") is None


def test_description_of_noise_only_suggests_nothing():
    # Nothing left to match on: suggesting would be a guess.
    history = [past(1, date(2026, 9, 1), "123 456")]

    assert suggest(history, "789") is None


def test_latest_label_of_each_key_in_one_pass():
    history = [
        past(1, date(2026, 9, 1), "CB SHOP 01.09.26", category_id=1),
        past(2, date(2026, 10, 1), "CB SHOP 01.10.26", category_id=2),
        past(3, date(2026, 8, 1), "CB OTHER 01.08.26", category_id=3),
        past(4, date(2026, 8, 1), "123 456", category_id=4),
    ]

    assert latest_by_key(history) == {
        "CB SHOP": Suggestion(2, date(2026, 10, 1)),
        "CB OTHER": Suggestion(3, date(2026, 8, 1)),
    }


def operation(operation_id, description):
    return Operation(operation_id, 1, date(2026, 10, 1), description, Decimal("-1"))


def test_similar_operations_share_the_key_and_include_the_operation():
    shop = operation(1, "ACHAT CB SHOP 28.10.26 CARTE NUMERO 195")
    others = [
        shop,
        operation(2, "ACHAT CB SHOP 02.11.26 CARTE NUMERO 195"),
        operation(3, "ACHAT CB OTHER 02.11.26"),
        operation(4, "achat cb shop carte numero"),
    ]

    assert similar_ids(shop, others) == [1, 2, 4]


def test_noise_only_operation_is_similar_to_nothing_but_itself():
    noise = operation(1, "123 456")

    assert similar_ids(noise, [noise, operation(2, "789")]) == [1]


SUGGESTION = Suggestion(1, date(2026, 10, 1))


@pytest.mark.parametrize(
    ("fields", "suggestion", "source"),
    [
        (LabelFields(1), SUGGESTION, LabelSource.SUGGESTION),
        (LabelFields(2), SUGGESTION, LabelSource.MANUAL),
        (LabelFields(1), None, LabelSource.MANUAL),
    ],
)
def test_source_is_suggestion_only_when_the_label_is_the_suggested_one(
    fields, suggestion, source
):
    assert source_of(fields, suggestion) == source
