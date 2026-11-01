import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from banking.models import Account

MAX_ID = 2**31 - 1  # largest INTEGER


def account_form(**overrides):
    return {
        "name": "Main account",
        "bank": "banque_postale",
        "type": "current",
        "account_number": "12345A",
        "opened_on": "2020-01-15",
    } | overrides


# The local database also holds seed data: compare counts, don't expect an empty table.
def count_accounts(session):
    return session.scalar(select(func.count()).select_from(Account))


def stored_number(session, name="Main account"):
    return session.scalar(select(Account.account_number).filter_by(name=name))


def declare(client, **overrides):
    response = client.post("/accounts", data=account_form(**overrides))
    assert response.status_code == 303
    return response.headers["location"]


def close(client, url, closed_on):
    return client.post(f"{url}/close", data={"closed_on": closed_on})


def test_declared_account_is_listed(client):
    url = declare(client)

    assert "Main account" in client.get("/").text
    page = client.get(url).text
    assert "La Banque Postale" in page
    assert "12345A" in page


def test_account_number_is_stored_without_spaces_and_uppercased(client, session):
    declare(client, account_number=" 12 345a ")

    assert stored_number(session) == "12345A"


def test_account_number_is_optional(client, session):
    declare(client, account_number="", bank="goodvest", type="life_insurance")

    assert stored_number(session) is None


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"account_number": "123 45a"}, "Another account already has this number."),
        ({"account_number": "999"}, "Another account already has this name."),
    ],
)
def test_duplicates_are_rejected_and_nothing_written(
    client, session, overrides, message
):
    declare(client)
    before = count_accounts(session)

    response = client.post("/accounts", data=account_form(**overrides))

    assert response.status_code == 422
    assert message in response.text
    assert count_accounts(session) == before


def test_invalid_fields_are_reported_and_nothing_written(client, session):
    before = count_accounts(session)

    response = client.post(
        "/accounts",
        data=account_form(
            name=" ", bank="other", account_number="12-34", opened_on="x"
        ),
    )

    assert response.status_code == 422
    assert response.text.count('class="error"') == 4
    assert count_accounts(session) == before


def test_html_in_a_name_is_escaped(client):
    url = declare(client, name="<script>x</script>")

    assert "<script>x" not in client.get(url).text
    assert "&lt;script&gt;x" in client.get("/").text


def test_edit_changes_the_account(client):
    url = declare(client)

    response = client.post(url, data=account_form(name="Renamed", type="savings"))

    assert response.status_code == 303
    page = client.get(url).text
    assert "Renamed" in page
    assert "Savings" in page


def test_edit_form_is_prefilled(client):
    url = declare(client)

    page = client.get(f"{url}/edit").text

    assert 'value="12345A"' in page
    assert 'value="2020-01-15"' in page


def test_closed_account_stays_visible(client):
    url = declare(client)

    assert close(client, url, "2026-03-31").status_code == 303

    assert "Closed on 2026-03-31" in client.get("/").text
    page = client.get(url).text
    assert "Main account" in page
    assert "Close account" not in page


def test_account_cannot_close_before_it_opened(client):
    url = declare(client)

    response = close(client, url, "2019-12-31")

    assert response.status_code == 422
    assert "can&#39;t close before it opened" in response.text
    assert "Close account" in client.get(url).text


def test_edit_cannot_open_a_closed_account_after_its_closing(client):
    url = declare(client)
    close(client, url, "2021-01-01")

    response = client.post(url, data=account_form(opened_on="2022-01-01"))

    assert response.status_code == 422
    assert "The account was closed before this date." in response.text


def test_closed_account_cannot_be_closed_again(client):
    url = declare(client)
    close(client, url, "2026-03-31")

    assert close(client, url, "2026-04-30").status_code == 409


def test_close_requires_a_date(client):
    url = declare(client)

    assert close(client, url, "").status_code == 422


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", f"/accounts/{MAX_ID}"),
        ("get", f"/accounts/{MAX_ID}/edit"),
        ("post", f"/accounts/{MAX_ID}"),
    ],
)
def test_unknown_account_is_not_found(client, method, path):
    data = {"data": account_form()} if method == "post" else {}

    assert getattr(client, method)(path, **data).status_code == 404


def test_account_id_beyond_the_integer_range_is_refused(client):
    # Regression: an id too large for INTEGER made Postgres fail (500).
    assert client.get(f"/accounts/{MAX_ID + 1}").status_code == 422


def test_nul_character_is_refused_and_nothing_written(client, session):
    # Regression: Postgres can't store NUL in text, the insert failed (500).
    before = count_accounts(session)

    response = client.post("/accounts", data=account_form(name="a\x00b"))

    assert response.status_code == 422
    assert count_accounts(session) == before


def test_cross_site_post_is_refused_and_nothing_written(client, session):
    before = count_accounts(session)

    response = client.post(
        "/accounts", data=account_form(), headers={"Sec-Fetch-Site": "cross-site"}
    )

    assert response.status_code == 403
    assert count_accounts(session) == before


def test_same_origin_post_is_accepted(client):
    response = client.post(
        "/accounts", data=account_form(), headers={"Sec-Fetch-Site": "same-origin"}
    )

    assert response.status_code == 303


@pytest.mark.parametrize(
    "overrides",
    [{"bank": "other"}, {"type": "other"}, {"closed_on": "2019-01-01"}],
)
def test_database_enforces_account_invariants(session, overrides):
    # Other writers (MCP server, jobs) will skip the web forms: the DB must refuse.
    row = {
        "name": "x",
        "bank": "cfcal",
        "type": "current",
        "opened_on": "2020-01-01",
        "closed_on": None,
    } | overrides

    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO banking.accounts (name, bank, type, opened_on, closed_on) "
                "VALUES (:name, :bank, :type, :opened_on, :closed_on)"
            ),
            row,
        )
