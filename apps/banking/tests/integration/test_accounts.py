"""Accounts in the admin: declare, edit, close and delete, within the constraints."""

from datetime import date

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from banking.databases.models import AccountModel, ImportModel, OperationModel

MAX_ID = 2**31 - 1  # largest INTEGER


@pytest.fixture
def account_form(admin, bank):
    """Make the admin account form's data, with overrides."""

    def make(**overrides):
        return {
            "csrftoken": admin.headers["X-CSRFToken"],
            "name": "Main account",
            "bank": str(bank.id),
            "type": "current",
            "account_number": "12345A",
            "opened_on": "2020-01-15",
        } | overrides

    return make


@pytest.fixture
def declare(admin, session, account_form):
    """Declare an account in the admin; return its id."""

    def post(**overrides):
        response = admin.post("/admin/accounts/create", data=account_form(**overrides))
        assert response.status_code == 303
        name = overrides.get("name", "Main account")
        return session.scalar(select(AccountModel.id).filter_by(name=name))

    return post


# The local database also holds seed data: compare counts, don't expect an empty table.
def count(session, model, **where):
    return session.scalar(select(func.count()).select_from(model).filter_by(**where))


def stored(session, account_id):
    """The account as stored now; None once deleted."""
    session.expire_all()
    query = select(AccountModel).filter_by(id=account_id)
    return session.scalars(query).one_or_none()


def close(admin, account_id, closed_on):
    return admin.post(
        "/admin/_api/accounts/row-action",
        params={"name": "close", "pk": account_id},
        data={"closed_on": closed_on},
    )


def test_declared_account_is_stored_and_listed(admin, session, declare, bank):
    account_id = declare(type="savings")

    account = stored(session, account_id)
    assert (account.bank_id, account.type, account.opened_on) == (
        bank.id,
        "savings",
        date(2020, 1, 15),
    )
    assert "Main account" in admin.get("/admin/accounts/list").text


def test_account_form_has_no_closing_date(admin):
    assert 'name="closed_on"' not in admin.get("/admin/accounts/create").text


def test_account_number_is_stored_without_spaces_and_uppercased(session, declare):
    assert stored(session, declare(account_number=" 12 345a ")).account_number == (
        "12345A"
    )


def test_account_number_is_optional(session, declare):
    account_id = declare(account_number="  ", type="life_insurance")

    assert stored(session, account_id).account_number is None


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"account_number": "123 45a"}, "Another account already has this number."),
        ({"account_number": "999"}, "Another account already has this name."),
        ({"name": "Other", "account_number": "12-34"}, "Letters and digits only"),
        ({"name": "Other", "account_number": "1" * 35}, "Letters and digits only"),
        ({"name": "Other", "account_number": "999", "opened_on": ""}, ""),
        ({"name": "Other", "account_number": "999", "bank": ""}, ""),
        ({"name": "Other", "account_number": "999", "type": "other"}, "Choose a type."),
        # Regression: Postgres can't store NUL in text, the insert failed (500).
        ({"name": "a\x00b", "account_number": "999"}, "Invalid character."),
    ],
)
def test_invalid_or_taken_fields_are_refused_on_their_field(
    admin, session, declare, account_form, overrides, message
):
    declare()
    before = count(session, AccountModel)

    response = admin.post("/admin/accounts/create", data=account_form(**overrides))

    assert response.status_code == 422
    assert message in response.text
    assert count(session, AccountModel) == before


def test_edit_changes_the_account(admin, session, declare, account_form):
    account_id = declare()

    response = admin.post(
        "/admin/accounts/edit",
        params={"pk": account_id},
        data=account_form(name="Renamed", type="pea"),
    )

    assert response.status_code == 303
    account = stored(session, account_id)
    assert (account.name, account.type) == ("Renamed", "pea")


def test_closed_account_keeps_its_data(admin, session, declare):
    account_id = declare()

    assert close(admin, account_id, "2026-03-31").status_code == 200

    account = stored(session, account_id)
    assert (account.name, account.closed_on) == ("Main account", date(2026, 3, 31))


def test_account_cannot_close_before_it_opened(admin, session, declare):
    account_id = declare()

    response = close(admin, account_id, "2019-12-31")

    assert response.status_code == 400
    assert "can't close before it opened" in response.json()["msg"]
    assert stored(session, account_id).closed_on is None


@pytest.mark.parametrize("closed_on", ["", "x"])
def test_close_requires_a_date(admin, session, declare, closed_on):
    account_id = declare()

    assert close(admin, account_id, closed_on).status_code == 400
    assert stored(session, account_id).closed_on is None


def test_closed_account_cannot_be_closed_again(admin, session, declare):
    account_id = declare()
    close(admin, account_id, "2026-03-31")

    assert close(admin, account_id, "2026-04-30").status_code == 400
    assert stored(session, account_id).closed_on == date(2026, 3, 31)


@pytest.mark.parametrize("pk", ["x", "0", str(MAX_ID + 1), str(MAX_ID)])
def test_unknown_or_invalid_id_is_refused(admin, pk):
    # Regression: a non-numeric id answered 500.
    assert close(admin, pk, "2026-03-31").status_code == 400
    assert admin.get("/admin/accounts/detail", params={"pk": pk}).status_code == 404


def test_edit_cannot_open_a_closed_account_after_its_closing(
    admin, declare, account_form
):
    account_id = declare()
    close(admin, account_id, "2021-01-01")

    response = admin.post(
        "/admin/accounts/edit",
        params={"pk": account_id},
        data=account_form(opened_on="2022-01-01"),
    )

    assert response.status_code == 422
    assert "The account was closed before this date." in response.text


@pytest.mark.parametrize("closed", [False, True])
def test_deleting_an_account_deletes_its_imports_and_operations(
    admin, session, account, add_operation, closed
):
    account_id = account.id
    add_operation(date(2026, 10, 1))
    if closed:
        close(admin, account_id, "2026-10-31")

    response = admin.post(
        "/admin/_api/accounts/row-action", params={"name": "delete", "pk": account_id}
    )

    assert response.status_code == 200
    assert stored(session, account_id) is None
    assert count(session, ImportModel, account_id=account_id) == 0
    assert count(session, OperationModel, account_id=account_id) == 0


def test_admin_refuses_a_cross_site_account_delete(admin, session, account):
    response = admin.post(
        "/admin/_api/accounts/action",
        params={"name": "delete", "pks": [str(account.id)]},
        headers={"sec-fetch-site": "cross-site"},
    )

    assert response.status_code == 403
    assert stored(session, account.id) is not None


@pytest.mark.parametrize(
    "overrides",
    [{"bank_id": MAX_ID}, {"type": "other"}, {"closed_on": "2019-01-01"}],
)
def test_database_enforces_account_invariants(session, bank, overrides):
    # The admin and other writers (MCP server, jobs) skip the services: the DB refuses.
    row = {
        "name": "x",
        "bank_id": bank.id,
        "type": "current",
        "opened_on": "2020-01-01",
        "closed_on": None,
    } | overrides

    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO banking.accounts "
                "(name, bank_id, type, opened_on, closed_on) "
                "VALUES (:name, :bank_id, :type, :opened_on, :closed_on)"
            ),
            row,
        )
