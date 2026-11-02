from datetime import date
from decimal import Decimal

import pytest

from banking.domains.operation import Operation
from banking.services.labels.matching import match_key, similar_ids


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
