import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from banking.databases.models import Account

MAX_ID = 2**31 - 1  # largest INTEGER


@pytest.fixture
def account_form(bank):
    def make(**overrides):
        return {
            "name": "Main account",
            "bank_id": str(bank.id),
            "type": "current",
            "account_number": "12345A",
            "opened_on": "2020-01-15",
        } | overrides

    return make


@pytest.fixture
def declare(client, account_form):
    """Declare an account; return its page URL."""

    def post(**overrides):
        response = client.post("/accounts", data=account_form(**overrides))
        assert response.status_code == 303
        return response.headers["location"]

    return post


# The local database also holds seed data: compare counts, don't expect an empty table.
def count_accounts(session):
    return session.scalar(select(func.count()).select_from(Account))


def stored_number(session, name="Main account"):
    return session.scalar(select(Account.account_number).filter_by(name=name))


def close(client, url, closed_on):
    return client.post(f"{url}/close", data={"closed_on": closed_on})


def test_declared_account_is_listed(client, declare):
    url = declare()

    assert "Main account" in client.get("/").text
    page = client.get(url).text
    assert "Test bank" in page
    assert "12345A" in page


def test_account_form_offers_the_banks(client, bank):
    page = client.get("/accounts/new").text

    assert f'<option value="{bank.id}"' in page
    assert "Test bank" in page


def test_account_number_is_stored_without_spaces_and_uppercased(session, declare):
    declare(account_number=" 12 345a ")

    assert stored_number(session) == "12345A"


def test_account_number_is_optional(session, declare):
    declare(account_number="", type="life_insurance")

    assert stored_number(session) is None


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"account_number": "123 45a"}, "Another account already has this number."),
        ({"account_number": "999"}, "Another account already has this name."),
        (
            {"name": "Other", "account_number": "999", "bank_id": str(MAX_ID)},
            "Unknown bank.",
        ),
    ],
)
def test_conflicts_are_rejected_and_nothing_written(
    client, session, declare, account_form, overrides, message
):
    declare()
    before = count_accounts(session)

    response = client.post("/accounts", data=account_form(**overrides))

    assert response.status_code == 422
    assert message in response.text
    assert count_accounts(session) == before


def test_invalid_fields_are_reported_and_nothing_written(client, session, account_form):
    before = count_accounts(session)

    response = client.post(
        "/accounts",
        data=account_form(
            name=" ", type="other", account_number="12-34", opened_on="x", bank_id="0"
        ),
    )

    assert response.status_code == 422
    assert response.text.count('class="error"') == 5
    assert count_accounts(session) == before


def test_html_in_a_name_is_escaped(client, declare):
    url = declare(name="<script>x</script>")

    assert "<script>x" not in client.get(url).text
    assert "&lt;script&gt;x" in client.get("/").text


def test_edit_changes_the_account(client, declare, account_form):
    url = declare()

    response = client.post(url, data=account_form(name="Renamed", type="savings"))

    assert response.status_code == 303
    page = client.get(url).text
    assert "Renamed" in page
    assert "Savings" in page


def test_edit_form_is_prefilled(client, declare, bank):
    url = declare()

    page = client.get(f"{url}/edit").text

    assert 'value="12345A"' in page
    assert 'value="2020-01-15"' in page
    assert f'<option value="{bank.id}" selected>' in page


def test_closed_account_stays_visible(client, declare):
    url = declare()

    assert close(client, url, "2026-03-31").status_code == 303

    assert "Closed on 2026-03-31" in client.get("/").text
    page = client.get(url).text
    assert "Main account" in page
    assert "Close account" not in page


def test_account_cannot_close_before_it_opened(client, declare):
    url = declare()

    response = close(client, url, "2019-12-31")

    assert response.status_code == 422
    assert "can&#39;t close before it opened" in response.text
    assert "Close account" in client.get(url).text


def test_edit_cannot_open_a_closed_account_after_its_closing(
    client, declare, account_form
):
    url = declare()
    close(client, url, "2021-01-01")

    response = client.post(url, data=account_form(opened_on="2022-01-01"))

    assert response.status_code == 422
    assert "The account was closed before this date." in response.text


def test_closed_account_cannot_be_closed_again(client, declare):
    url = declare()
    close(client, url, "2026-03-31")

    assert close(client, url, "2026-04-30").status_code == 409


def test_close_requires_a_date(client, declare):
    url = declare()

    assert close(client, url, "").status_code == 422


def test_deleted_account_is_gone(client, session, declare):
    url = declare()
    before = count_accounts(session)

    response = client.post(f"{url}/delete")

    assert response.status_code == 303
    assert count_accounts(session) == before - 1
    assert "Main account" not in client.get("/").text
    assert client.get(url).status_code == 404


def test_closed_account_can_be_deleted(client, declare):
    url = declare()
    close(client, url, "2026-03-31")

    assert client.post(f"{url}/delete").status_code == 303
    assert client.get(url).status_code == 404


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", f"/accounts/{MAX_ID}"),
        ("get", f"/accounts/{MAX_ID}/edit"),
        ("post", f"/accounts/{MAX_ID}"),
        ("post", f"/accounts/{MAX_ID}/delete"),
    ],
)
def test_unknown_account_is_not_found(client, account_form, method, path):
    data = {"data": account_form()} if method == "post" else {}

    assert getattr(client, method)(path, **data).status_code == 404


def test_account_id_beyond_the_integer_range_is_refused(client):
    # Regression: an id too large for INTEGER made Postgres fail (500).
    assert client.get(f"/accounts/{MAX_ID + 1}").status_code == 422


def test_nul_character_is_refused_and_nothing_written(client, session, account_form):
    # Regression: Postgres can't store NUL in text, the insert failed (500).
    before = count_accounts(session)

    response = client.post("/accounts", data=account_form(name="a\x00b"))

    assert response.status_code == 422
    assert count_accounts(session) == before


@pytest.mark.parametrize("action", ["", "/delete"])
def test_cross_site_post_is_refused_and_nothing_changed(
    client, session, declare, account_form, action
):
    url = declare()
    before = count_accounts(session)

    response = client.post(
        f"{url}{action}",
        data=account_form(name="Renamed"),
        headers={"Sec-Fetch-Site": "cross-site"},
    )

    assert response.status_code == 403
    assert count_accounts(session) == before
    assert "Main account" in client.get(url).text


def test_same_origin_post_is_accepted(client, account_form):
    response = client.post(
        "/accounts", data=account_form(), headers={"Sec-Fetch-Site": "same-origin"}
    )

    assert response.status_code == 303


@pytest.mark.parametrize(
    "overrides",
    [{"bank_id": MAX_ID}, {"type": "other"}, {"closed_on": "2019-01-01"}],
)
def test_database_enforces_account_invariants(session, bank, overrides):
    # Other writers (MCP server, jobs) will skip the web forms: the DB must refuse.
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
