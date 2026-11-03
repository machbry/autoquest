"""The Import page: data freshness, import of an export file, monthly recap."""

import html
import logging
import re
from datetime import date, timedelta
from decimal import Decimal

import pytest
from faker import Faker
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from banking.api.schemas.common import MAX_ID
from banking.databases.models import ImportModel, OperationModel
from banking.domains.operation import OperationFields
from banking.services.imports.banque_postale_csv import FIRST_ROW_LINE
from banking.services.imports.import_service import MAX_FILE_BYTES
from banking.tools.fakes import build_export, fake_operations

NUMBER = "12345A"  # the `main` account's number
TODAY = date.today()


@pytest.fixture
def fake():
    fake = Faker()
    fake.seed_instance(12)
    return fake


@pytest.fixture
def main(add_account):
    """The id of an account with a number, to import its exports."""
    return add_account("Main account", account_number=NUMBER).id


def page(client, account_id):
    """The Import page, showing this account."""
    return client.get("/imports", params={"account_id": account_id}).text


def upload(client, account_id, content, **kwargs):
    return client.post(
        f"/accounts/{account_id}/imports",
        files={"file": ("export.csv", content, "text/csv")},
        **kwargs,
    )


def imported(client, account_id, content):
    """Import a file; return the Import page showing its summary."""
    response = upload(client, account_id, content)
    assert response.status_code == 303
    location = response.headers["location"]
    assert re.fullmatch(rf"/imports\?account_id={account_id}&import_id=\d+", location)
    return client.get(location).text


def export(operations, export_date=TODAY, number=NUMBER, **options):
    return build_export(number, export_date, operations, **options)


def operation(day=1, description="CB SHOP", amount="-12.34"):
    return OperationFields(TODAY - timedelta(days=day), description, Decimal(amount))


# The local database also holds seed data: count the test account's rows only.
def count(session, model, account_id):
    return session.scalar(
        select(func.count()).select_from(model).where(model.account_id == account_id)
    )


def assert_rejected(client, session, account_id, content, message):
    response = upload(client, account_id, content)

    assert response.status_code == 422
    assert message in response.text.replace("&#39;", "'")
    assert count(session, ImportModel, account_id) == 0
    assert count(session, OperationModel, account_id) == 0


def test_import_stores_every_operation_and_shows_a_summary(client, session, main, fake):
    operations = fake_operations(fake, TODAY - timedelta(days=89), TODAY)
    dates = [row.operation_date for row in operations]

    page = imported(client, main, export(operations))

    n = len(operations)
    assert count(session, OperationModel, main) == n
    assert f"{n} rows in the file: {n} new, 0 already known." in page
    assert f"Operations from {min(dates)} to {max(dates)}." in page


def test_importing_the_same_file_again_adds_nothing(client, session, main, fake):
    content = export(fake_operations(fake, TODAY - timedelta(days=30), TODAY))
    imported(client, main, content)
    stored = count(session, OperationModel, main)

    page = imported(client, main, content)

    assert count(session, OperationModel, main) == stored
    assert f"{stored} rows in the file: 0 new, {stored} already known." in page
    assert count(session, ImportModel, main) == 2


def test_identical_rows_are_both_stored(client, session, main):
    imported(client, main, export([operation(), operation()]))

    assert count(session, OperationModel, main) == 2


def test_overlapping_export_adds_only_what_is_new(client, session, main, fake):
    start = TODAY - timedelta(days=89)
    operations = fake_operations(fake, start, TODAY)
    a = [row for row in operations if row.operation_date < start + timedelta(days=60)]
    b = [row for row in operations if row.operation_date >= start + timedelta(days=30)]
    # A second copy of an operation that A already holds: a real, new operation.
    b.append(b[0])
    imported(client, main, export(a, start + timedelta(days=59)))

    page = imported(client, main, export(b))

    added = len(operations) + 1 - len(a)
    assert count(session, OperationModel, main) == len(operations) + 1
    assert f"{len(b)} rows in the file: {added} new" in page


def test_export_of_another_account_is_rejected(client, session, main):
    content = export([operation()], number="99999Z")

    assert_rejected(
        client, session, main, content, "This file belongs to another account."
    )


def test_account_number_is_compared_without_spaces_or_case(client, session, main):
    imported(client, main, export([operation()], number="123 45a"))

    assert count(session, OperationModel, main) == 1


def test_account_without_a_number_is_refused(client, session, add_account):
    account_id = add_account("No number").id

    assert_rejected(
        client,
        session,
        account_id,
        export([operation()]),
        "Set this account's number before importing.",
    )


def test_malformed_amount_is_rejected_with_its_line(client, session, main):
    content = export([operation(1), operation(2)]).replace(
        b"-12,34\r\n", b"-12.34\r\n", 1
    )

    assert_rejected(
        client, session, main, content, f"Line {FIRST_ROW_LINE}: invalid amount."
    )


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"\x89PNG\r\n\x1a\n\x00", "This file isn't a La Banque Postale CSV file."),
        (b"", "This file isn't a La Banque Postale CSV file."),
        (export([operation()], currency="dollars"), "Only files in euros"),
        (b"x" * (MAX_FILE_BYTES + 1), "The file is over 1 MB."),
        # Regression: csv.Error on a stray carriage return answered 500.
        (
            export([operation(description="CB\rSHOP")]).replace(b'"', b""),
            f"Line {FIRST_ROW_LINE}: malformed line.",
        ),
        # Regression: a future date made freshness negative, and OK, for good.
        (export([], TODAY + timedelta(days=1)), "The file's date is in the future."),
    ],
)
def test_unreadable_or_unsupported_file_is_rejected(
    client, session, main, content, message
):
    assert_rejected(client, session, main, content, message)


def test_missing_file_is_rejected(client, session, main):
    response = client.post(
        f"/accounts/{main}/imports", files={"other": ("export.csv", export([]))}
    )

    assert response.status_code == 422
    assert count(session, ImportModel, main) == 0


def test_much_larger_upload_is_refused_before_reading(client, main):
    response = upload(client, main, b"x" * (2 * MAX_FILE_BYTES + 1))

    assert response.status_code == 413


def test_upload_without_a_declared_length_is_refused(client, main):
    # Regression: a chunked body skipped the size check and was spooled whole.
    response = client.post(f"/accounts/{main}/imports", content=iter([export([])]))

    assert response.status_code == 411


def test_upload_with_an_invalid_length_is_refused(client, main):
    # Regression: a non-numeric Content-Length answered 500.
    response = client.post(
        f"/accounts/{main}/imports", content=b"", headers={"Content-Length": "x"}
    )

    assert response.status_code == 400


def test_closed_account_keeps_its_operations_and_still_imports(admin, main):
    imported(admin, main, export([operation(description="CB BEFORE CLOSE")]))
    response = admin.post(
        "/admin/_api/accounts/row-action",
        params={"name": "close", "pk": main},
        data={"closed_on": str(TODAY)},
    )
    assert response.status_code == 200

    imported(admin, main, export([operation(description="CB LAST ONE")]))

    text = admin.get(
        "/admin/operations/list", params={"filter": f"account__in={main}"}
    ).text
    assert "CB BEFORE CLOSE" in text
    assert "CB LAST ONE" in text


def test_amounts_are_stored_exact_to_the_cent(client, session, main):
    rows = [
        operation(1, "A", "0.10"),
        operation(2, "B", "0.20"),
        operation(3, "C", "-0.30"),
    ]
    imported(client, main, export(rows))

    total = session.scalar(
        select(func.sum(OperationModel.amount)).where(OperationModel.account_id == main)
    )
    assert total == Decimal("0.00")


@pytest.mark.parametrize(
    ("days", "label"),
    [
        (60, 'class="ok">File dated 60 days ago<'),
        (61, 'class="warning">File dated 61 days ago: import a new file soon<'),
        (76, 'class="alert">File dated 76 days ago: import a new file now<'),
    ],
)
def test_freshness_counts_days_since_the_latest_export(client, main, days, label):
    imported(client, main, export([], TODAY - timedelta(days=days)))

    assert label in page(client, main)
    assert label in client.get("/imports").text


def test_older_export_does_not_reset_freshness(client, main):
    imported(client, main, export([operation(80)], TODAY - timedelta(days=76)))

    imported(client, main, export([operation(100)], TODAY - timedelta(days=95)))

    assert "File dated 76 days ago" in page(client, main)


def test_account_never_imported_says_so(client, main):
    assert "Never imported" in page(client, main)


def test_unknown_import_id_shows_no_summary(client, main):
    response = client.get("/imports", params={"account_id": main, "import_id": MAX_ID})

    assert response.status_code == 200
    assert "File imported" not in response.text


def test_import_logs_no_personal_data(client, main, caplog):
    caplog.set_level(logging.DEBUG)

    imported(client, main, export([operation(description="CB SECRET SHOP")]))
    upload(client, main, export([operation(description="CB OTHER")], number="99Z"))

    assert "import" in caplog.text
    for secret in ("SECRET", "OTHER", "12,34", "12.34", NUMBER, "99Z"):
        assert secret not in caplog.text


def test_cross_site_import_is_refused(client, session, main):
    response = upload(
        client,
        main,
        export([operation()]),
        headers={"Sec-Fetch-Site": "cross-site"},
    )

    assert response.status_code == 403
    assert count(session, OperationModel, main) == 0


def test_import_into_an_unknown_account_is_not_found(client):
    assert upload(client, MAX_ID, export([operation()])).status_code == 404


@pytest.mark.parametrize(
    ("occurrence", "constraint"),
    [(1, "uq_operations_occurrence"), (0, "ck_operations_occurrence_positive")],
)
def test_database_enforces_operation_invariants(
    client, session, main, occurrence, constraint
):
    # Other writers (MCP server, jobs) will skip the import: the DB must refuse.
    imported(client, main, export([operation()]))
    row = session.execute(
        select(OperationModel.import_id, OperationModel.operation_date).where(
            OperationModel.account_id == main
        )
    ).one()

    with pytest.raises(IntegrityError, match=constraint):
        session.execute(
            text(
                "INSERT INTO banking.operations "
                "(account_id, import_id, operation_date, description, amount, "
                "occurrence) "
                "VALUES (:account_id, :import_id, :operation_date, 'CB SHOP', -12.34, "
                ":occurrence)"
            ),
            {
                "account_id": main,
                "import_id": row.import_id,
                "operation_date": row.operation_date,
                "occurrence": occurrence,
            },
        )


def test_home_redirects_to_the_import_page(client):
    response = client.get("/")

    assert response.status_code == 307
    assert response.headers["location"] == "/imports"


def test_import_page_lists_every_account_open_ones_first(client, session, add_account):
    add_account("Test B open")
    closed = add_account("Test A closed")
    closed.closed_on = date(2026, 3, 31)
    session.commit()
    add_account("Test C <script>")

    text = client.get("/imports").text

    names = re.findall(r'account_id=\d+"(?: [^>]*)?>(Test [^<]+)<', text)
    assert names == ["Test B open", "Test C &lt;script&gt;", "Test A closed"]
    assert "Closed on 2026-03-31" in text


@pytest.mark.parametrize(
    ("account_id", "status"), [(MAX_ID, 404), (MAX_ID + 1, 422), (0, 422)]
)
def test_unknown_or_out_of_range_account_is_refused(client, account_id, status):
    # Regression: an id too large for INTEGER made Postgres fail (500).
    response = client.get("/imports", params={"account_id": account_id})

    assert response.status_code == status


def test_import_page_recaps_operations_by_month(
    client, account, add_account, add_operation, groceries
):
    october = [
        add_operation(date(2026, 10, 1), category=groceries),
        add_operation(date(2026, 10, 31)),
    ]
    november = add_operation(date(2026, 11, 2))
    add_operation(date(2026, 10, 15), target=add_account("Other account"))

    text = re.sub(r"\s+", " ", page(client, account.id))

    rows = re.findall(r'<tr> <td><a href="([^"]+)">([\d-]+)</a></td>(.*?)</tr>', text)
    assert [month for _, month, _ in rows] == ["2026-11", "2026-10"]
    counts = [
        re.findall(r'class="num">(?:<a [^>]*>)?(\d+)', cells) for *_, cells in rows
    ]
    assert counts == [["1", "0", "1"], ["2", "1", "1"]]
    # Each month links to the admin's table of its operations, all or unlabelled.
    links = re.findall(r'href="(/admin/operations/list\?filter=[^"]+)"', text)
    links = [html.unescape(link) for link in links]
    assert [listed_ids(client, link) for link in links] == [
        [november.id],
        [november.id],
        [october[1].id, october[0].id],
        [october[1].id],
    ]
    # The recap replaces the operation list.
    assert "LABELTEST" not in text


def listed_ids(client, url):
    """The ids of the operations an admin list page shows, in order."""
    response = client.get(url)
    assert response.status_code == 200
    return [int(pk) for pk in re.findall(r'<tr data-sa-pk="(\d+)"', response.text)]


def test_account_without_operations_says_so(client, account):
    assert "No operation yet." in page(client, account.id)


def test_import_page_links_to_the_account_in_the_admin(client, account):
    link = re.search(
        r'href="(/admin/accounts/detail\?pk=\d+)"', page(client, account.id)
    )

    assert client.get(link[1]).status_code == 200
