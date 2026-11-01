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
from banking.fakes import build_export, fake_operations
from banking.services.imports.banque_postale_csv import FIRST_ROW_LINE
from banking.services.imports.import_service import MAX_FILE_BYTES

NUMBER = "12345A"  # the `declare` fixture's account number
TODAY = date.today()


@pytest.fixture
def fake():
    fake = Faker()
    fake.seed_instance(12)
    return fake


@pytest.fixture
def account_url(declare):
    return declare()


def account_id(url):
    return int(url.rsplit("/", 1)[1])


def upload(client, url, content, **kwargs):
    return client.post(
        f"{url}/imports", files={"file": ("export.csv", content, "text/csv")}, **kwargs
    )


def imported(client, url, content):
    """Import a file; return the account page showing its summary."""
    response = upload(client, url, content)
    assert response.status_code == 303
    location = response.headers["location"]
    assert re.fullmatch(rf"{url}\?import_id=\d+", location)
    return client.get(location).text


def export(operations, export_date=TODAY, number=NUMBER, **options):
    return build_export(number, export_date, operations, **options)


def operation(day=1, description="CB SHOP", amount="-12.34"):
    return OperationFields(TODAY - timedelta(days=day), description, Decimal(amount))


# The local database also holds seed data: count the test account's rows only.
def count(session, model, url):
    return session.scalar(
        select(func.count())
        .select_from(model)
        .where(model.account_id == account_id(url))
    )


def assert_rejected(client, session, url, content, message):
    response = upload(client, url, content)

    assert response.status_code == 422
    assert message in response.text.replace("&#39;", "'")
    assert count(session, ImportModel, url) == 0
    assert count(session, OperationModel, url) == 0


def test_import_stores_every_operation_and_shows_a_summary(
    client, session, account_url, fake
):
    operations = fake_operations(fake, TODAY - timedelta(days=89), TODAY)
    first = min(row.operation_date for row in operations)

    page = imported(client, account_url, export(operations))

    n = len(operations)
    assert count(session, OperationModel, account_url) == n
    assert f"{n} rows in the file: {n} new, 0 already known." in page
    assert f"Operations from {first} to {TODAY}." in page


def test_importing_the_same_file_again_adds_nothing(client, session, account_url, fake):
    content = export(fake_operations(fake, TODAY - timedelta(days=30), TODAY))
    imported(client, account_url, content)
    stored = count(session, OperationModel, account_url)

    page = imported(client, account_url, content)

    assert count(session, OperationModel, account_url) == stored
    assert f"{stored} rows in the file: 0 new, {stored} already known." in page
    assert count(session, ImportModel, account_url) == 2


def test_identical_rows_are_both_stored(client, session, account_url):
    imported(client, account_url, export([operation(), operation()]))

    assert count(session, OperationModel, account_url) == 2


def test_overlapping_export_adds_only_what_is_new(client, session, account_url, fake):
    start = TODAY - timedelta(days=89)
    operations = fake_operations(fake, start, TODAY)
    a = [row for row in operations if row.operation_date < start + timedelta(days=60)]
    b = [row for row in operations if row.operation_date >= start + timedelta(days=30)]
    # A second copy of an operation that A already holds: a real, new operation.
    b.append(b[0])
    imported(client, account_url, export(a, start + timedelta(days=59)))

    page = imported(client, account_url, export(b))

    added = len(operations) + 1 - len(a)
    assert count(session, OperationModel, account_url) == len(operations) + 1
    assert f"{len(b)} rows in the file: {added} new" in page


def test_export_of_another_account_is_rejected(client, session, account_url):
    content = export([operation()], number="99999Z")

    assert_rejected(
        client, session, account_url, content, "This file is another account's export."
    )


def test_account_number_is_compared_without_spaces_or_case(
    client, session, account_url
):
    imported(client, account_url, export([operation()], number="123 45a"))

    assert count(session, OperationModel, account_url) == 1


def test_account_without_a_number_is_refused(client, session, declare):
    url = declare(account_number="", type="current")

    assert_rejected(
        client,
        session,
        url,
        export([operation()]),
        "Set this account's number before importing.",
    )


def test_malformed_amount_is_rejected_with_its_line(client, session, account_url):
    content = export([operation(1), operation(2)]).replace(
        b"-12,34\r\n", b"-12.34\r\n", 1
    )

    assert_rejected(
        client, session, account_url, content, f"Line {FIRST_ROW_LINE}: invalid amount."
    )


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"\x89PNG\r\n\x1a\n\x00", "This file isn't a Banque Postale CSV export."),
        (b"", "This file isn't a Banque Postale CSV export."),
        (export([operation()], currency="dollars"), "Only exports in euros"),
        (b"x" * (MAX_FILE_BYTES + 1), "The file is over 1 MB."),
        # Regression: csv.Error on a stray carriage return answered 500.
        (
            export([operation(description="CB\rSHOP")]).replace(b'"', b""),
            f"Line {FIRST_ROW_LINE}: malformed line.",
        ),
        # Regression: a future date made freshness negative, and OK, for good.
        (export([], TODAY + timedelta(days=1)), "The export date is in the future."),
    ],
)
def test_unreadable_or_unsupported_file_is_rejected(
    client, session, account_url, content, message
):
    assert_rejected(client, session, account_url, content, message)


def test_missing_file_is_rejected(client, session, account_url):
    response = client.post(
        f"{account_url}/imports", files={"other": ("export.csv", export([]))}
    )

    assert response.status_code == 422
    assert count(session, ImportModel, account_url) == 0


def test_much_larger_upload_is_refused_before_reading(client, account_url):
    response = upload(client, account_url, b"x" * (2 * MAX_FILE_BYTES + 1))

    assert response.status_code == 413


def test_upload_without_a_declared_length_is_refused(client, account_url):
    # Regression: a chunked body skipped the size check and was spooled whole.
    response = client.post(f"{account_url}/imports", content=iter([export([])]))

    assert response.status_code == 411


def test_upload_with_an_invalid_length_is_refused(client, account_url):
    # Regression: a non-numeric Content-Length answered 500.
    response = client.post(
        f"{account_url}/imports", content=b"", headers={"Content-Length": "x"}
    )

    assert response.status_code == 400


def test_closed_account_keeps_its_operations_and_still_imports(client, account_url):
    imported(client, account_url, export([operation(description="CB BEFORE CLOSE")]))
    response = client.post(f"{account_url}/close", data={"closed_on": str(TODAY)})
    assert response.status_code == 303

    page = imported(client, account_url, export([operation(description="CB LAST ONE")]))

    assert "CB BEFORE CLOSE" in page
    assert "CB LAST ONE" in page


def test_amounts_are_stored_exact_to_the_cent(client, session, account_url):
    rows = [
        operation(1, "A", "0.10"),
        operation(2, "B", "0.20"),
        operation(3, "C", "-0.30"),
    ]
    imported(client, account_url, export(rows))

    total = session.scalar(
        select(func.sum(OperationModel.amount)).where(
            OperationModel.account_id == account_id(account_url)
        )
    )
    assert total == Decimal("0.00")


@pytest.mark.parametrize(
    ("days", "label"),
    [
        (60, 'class="ok">Exported 60 days ago<'),
        (61, 'class="warning">Exported 61 days ago: export soon<'),
        (76, 'class="alert">Exported 76 days ago: export now<'),
    ],
)
def test_freshness_counts_days_since_the_latest_export(
    client, account_url, days, label
):
    imported(client, account_url, export([], TODAY - timedelta(days=days)))

    assert label in client.get(account_url).text
    assert label in client.get("/accounts").text


def test_older_export_does_not_reset_freshness(client, account_url):
    imported(client, account_url, export([operation(80)], TODAY - timedelta(days=76)))

    imported(client, account_url, export([operation(100)], TODAY - timedelta(days=95)))

    assert "Exported 76 days ago" in client.get(account_url).text


def test_account_never_imported_says_so(client, account_url):
    assert "Never imported" in client.get(account_url).text


def test_unknown_import_id_shows_no_summary(client, account_url):
    page = client.get(f"{account_url}?import_id={MAX_ID}")

    assert page.status_code == 200
    assert "Export imported" not in page.text


def test_deleting_an_account_deletes_its_imports_and_operations(
    client, session, account_url
):
    imported(client, account_url, export([operation()]))

    assert client.post(f"{account_url}/delete").status_code == 303

    assert count(session, ImportModel, account_url) == 0
    assert count(session, OperationModel, account_url) == 0


def test_import_logs_no_personal_data(client, account_url, caplog):
    caplog.set_level(logging.DEBUG)

    imported(client, account_url, export([operation(description="CB SECRET SHOP")]))
    upload(
        client, account_url, export([operation(description="CB OTHER")], number="99Z")
    )

    assert "import" in caplog.text
    for secret in ("SECRET", "OTHER", "12,34", "12.34", NUMBER, "99Z"):
        assert secret not in caplog.text


def test_cross_site_import_is_refused(client, session, account_url):
    response = upload(
        client,
        account_url,
        export([operation()]),
        headers={"Sec-Fetch-Site": "cross-site"},
    )

    assert response.status_code == 403
    assert count(session, OperationModel, account_url) == 0


def test_import_into_an_unknown_account_is_not_found(client):
    assert (
        upload(client, f"/accounts/{MAX_ID}", export([operation()])).status_code == 404
    )


@pytest.mark.parametrize(
    ("occurrence", "constraint"),
    [(1, "uq_operations_occurrence"), (0, "ck_operations_occurrence_positive")],
)
def test_database_enforces_operation_invariants(
    client, session, account_url, occurrence, constraint
):
    # Other writers (MCP server, jobs) will skip the import: the DB must refuse.
    imported(client, account_url, export([operation()]))
    row = session.execute(
        select(OperationModel.import_id, OperationModel.operation_date).where(
            OperationModel.account_id == account_id(account_url)
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
                "account_id": account_id(account_url),
                "import_id": row.import_id,
                "operation_date": row.operation_date,
                "occurrence": occurrence,
            },
        )
