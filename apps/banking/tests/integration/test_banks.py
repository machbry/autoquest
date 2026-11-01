import re

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from banking.models import Account, AccountType, Bank

MAX_ID = 2**31 - 1  # largest INTEGER


# The local database also holds seed data: compare counts, don't expect an empty table.
def count_banks(session):
    return session.scalar(select(func.count()).select_from(Bank))


@pytest.fixture
def account(session, bank):
    account = Account(
        name="Main account",
        bank=bank,
        type=AccountType.CURRENT,
        opened_on="2020-01-15",
    )
    session.add(account)
    session.commit()
    return account


def test_added_bank_is_listed(client):
    response = client.post("/banks", data={"name": "  My bank  "})

    assert response.status_code == 303
    assert "My bank" in client.get("/banks").text


@pytest.mark.parametrize(
    ("name", "message"),
    [
        (" ", "at least 1 character"),
        ("Test bank", "Another bank already has this name."),
    ],
)
def test_invalid_or_duplicate_name_is_rejected_and_nothing_written(
    client, session, bank, name, message
):
    before = count_banks(session)

    response = client.post("/banks", data={"name": name})

    assert response.status_code == 422
    assert message in response.text
    assert count_banks(session) == before


def test_rename_changes_the_bank(client, bank):
    assert 'value="Test bank"' in client.get(f"/banks/{bank.id}/edit").text

    response = client.post(f"/banks/{bank.id}", data={"name": "Renamed bank"})

    assert response.status_code == 303
    page = client.get("/banks").text
    assert "Renamed bank" in page
    assert "Test bank" not in page


def test_rename_to_a_taken_name_is_rejected(client, session, bank):
    other = Bank(name="Other bank")
    session.add(other)
    session.commit()

    response = client.post(f"/banks/{other.id}", data={"name": "Test bank"})

    assert response.status_code == 422
    assert "Another bank already has this name." in response.text


def test_unused_bank_can_be_deleted(client, session, bank):
    before = count_banks(session)

    response = client.post(f"/banks/{bank.id}/delete")

    assert response.status_code == 303
    assert count_banks(session) == before - 1
    assert "Test bank" not in client.get("/banks").text


def test_bank_in_use_cannot_be_deleted(client, session, bank, account):
    before = count_banks(session)

    response = client.post(f"/banks/{bank.id}/delete")

    assert response.status_code == 409
    assert "Accounts still use this bank." in response.text
    assert count_banks(session) == before
    assert "Test bank" in client.get(f"/accounts/{account.id}").text


def test_bank_list_counts_accounts(client, account):
    page = re.sub(r"\s+", " ", client.get("/banks").text)

    assert "<td>Test bank</td> <td>1</td>" in page


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", f"/banks/{MAX_ID}/edit"),
        ("post", f"/banks/{MAX_ID}"),
        ("post", f"/banks/{MAX_ID}/delete"),
    ],
)
def test_unknown_bank_is_not_found(client, method, path):
    data = {"data": {"name": "x"}} if method == "post" else {}

    assert getattr(client, method)(path, **data).status_code == 404


def test_cross_site_delete_is_refused(client, session, bank):
    response = client.post(
        f"/banks/{bank.id}/delete", headers={"Sec-Fetch-Site": "cross-site"}
    )

    assert response.status_code == 403
    assert session.get(Bank, bank.id) is not None


def test_database_refuses_to_delete_a_bank_in_use(session, bank, account):
    # Other writers will skip the web app: the foreign key must refuse.
    with pytest.raises(IntegrityError):
        session.execute(
            text("DELETE FROM banking.banks WHERE id = :id"), {"id": bank.id}
        )
