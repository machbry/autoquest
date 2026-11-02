import re
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text

from banking.databases.models import (
    AccountModel,
    CategoryModel,
    ImportModel,
    LabelModel,
    OperationModel,
)
from banking.domains.account import AccountType
from banking.domains.label import LabelSource

MAX_ID = 2**31 - 1  # largest INTEGER
HTMX = {"HX-Request": "true"}
# Payees no seed operation uses: the seed's labels must not suggest anything here.
SHOP = "ACHAT CB LABELTEST SHOP {:%d.%m.%y} CARTE NUMERO 195"
OTHER = "PRLV SEPA LABELTEST OTHER {:%d%m}"


@pytest.fixture
def account(session, bank):
    account = AccountModel(
        name="Label account",
        bank=bank,
        type=AccountType.CURRENT,
        opened_on=date(2020, 1, 15),
    )
    session.add(account)
    session.commit()
    return account


@pytest.fixture
def add_operation(session, account):
    """Add an operation to the account; return it."""
    imported = ImportModel(
        account_id=account.id,
        export_date=date(2026, 11, 2),
        balance=Decimal("100.00"),
        rows_in_file=0,
        rows_new=0,
    )
    session.add(imported)
    session.flush()

    def make(day, description=None, target=account):
        operation = OperationModel(
            account_id=target.id,
            import_id=imported.id,
            operation_date=day,
            description=(description or SHOP).format(day),
            amount=Decimal("-9.99"),
            occurrence=1,
        )
        session.add(operation)
        session.commit()
        return operation

    return make


@pytest.fixture
def groceries(session):
    return add_category(session, "Test groceries")


@pytest.fixture
def leisure(session):
    return add_category(session, "Test leisure")


def add_category(session, name):
    category = CategoryModel(name=name)
    session.add(category)
    session.commit()
    return category


def add_label(session, operation, category, tags=(), source=LabelSource.MANUAL):
    label = LabelModel(
        operation_id=operation.id,
        category_id=category.id,
        tags=list(tags),
        source=source,
    )
    session.add(label)
    session.commit()
    return label


def stored(session, operation):
    session.expire_all()
    return session.get(LabelModel, operation.id)


def queue(client, operation, **params):
    """The queue of the operation's account."""
    return client.get(
        "/labels/new", params={"account_id": operation.account_id, **params}
    )


def label_form(operation, category, **overrides):
    return {
        "operation_id": str(operation.id),
        "category_id": str(category.id),
        "account_id": str(operation.account_id),
        "month": "",
        "tag_1": "",
        "tag_2": "",
        "tag_3": "",
        "note": "",
        "scope": "one",
    } | overrides


def shown_operation_id(page):
    return int(re.search(r'name="operation_id" value="(\d+)"', page)[1])


# The queue shows its form only once a category exists: tests that read the form ask
# for one (`groceries`), as CI's database is empty.
def test_queue_shows_the_remaining_count_and_the_oldest_first(
    client, add_operation, groceries
):
    add_operation(date(2026, 10, 3))
    oldest = add_operation(date(2026, 10, 1), OTHER)
    add_operation(date(2026, 10, 2))

    page = queue(client, oldest).text

    assert "3 to label" in page
    assert shown_operation_id(page) == oldest.id
    assert "PRLV SEPA LABELTEST OTHER 0110" in page


def test_matching_history_is_suggested(
    client, session, add_operation, groceries, leisure
):
    past = add_operation(date(2026, 10, 28))
    add_label(session, past, leisure, ["Holiday", "Lisbon"])
    add_operation(date(2026, 11, 2))

    page = queue(client, past).text

    assert "Suggested from the operation of 2026-10-28." in page
    assert f'<option value="{leisure.id}" selected>' in page
    assert 'name="tag_1" value="Holiday"' in page
    assert 'name="tag_2" value="Lisbon"' in page
    # One keystroke: Enter on the focused Save button.
    assert 'value="one" autofocus>Save</button>' in page


def test_accepting_the_suggestion_stores_it_as_such_and_shows_the_next(
    client, session, add_operation, leisure
):
    past = add_operation(date(2026, 10, 28))
    add_label(session, past, leisure, ["Holiday"])
    current = add_operation(date(2026, 11, 1))
    following = add_operation(date(2026, 11, 2), OTHER)

    response = client.post(
        "/labels", data=label_form(current, leisure, tag_1="Holiday")
    )

    assert response.status_code == 303
    assert response.headers["location"] == f"/labels/new?account_id={past.account_id}"
    assert stored(session, current).source == LabelSource.SUGGESTION
    page = client.get(response.headers["location"]).text
    assert "1 to label" in page
    assert shown_operation_id(page) == following.id


@pytest.mark.parametrize("with_history", [True, False])
def test_label_set_by_hand_is_manual(
    client, session, add_operation, groceries, leisure, with_history
):
    if with_history:
        add_label(session, add_operation(date(2026, 10, 28)), leisure, ["Holiday"])
    current = add_operation(date(2026, 11, 2))

    response = client.post(
        "/labels", data=label_form(current, groceries, tag_1="Holiday")
    )

    assert response.status_code == 303
    assert stored(session, current).source == LabelSource.MANUAL


def test_no_matching_history_suggests_nothing(client, session, add_operation, leisure):
    add_label(session, add_operation(date(2026, 10, 28), OTHER), leisure)
    current = add_operation(date(2026, 11, 2))

    page = queue(client, current).text

    assert "Suggested from" not in page
    assert " selected>" not in page.split('name="category_id"')[1].split("</select>")[0]
    assert '<select name="category_id" required autofocus>' in page


def test_empty_queue_says_nothing_to_label(client, session, add_operation, leisure):
    labelled = add_operation(date(2026, 11, 2))
    add_label(session, labelled, leisure)

    page = queue(client, labelled).text

    assert "Nothing to label." in page
    assert 'action="/labels"' not in page


def test_save_for_all_similar_labels_them_alike(
    client, session, add_operation, groceries
):
    similar = [add_operation(date(2026, 10, day)) for day in (1, 5, 9)]
    different = add_operation(date(2026, 10, 2), OTHER)
    page = queue(client, different).text
    assert "Save for all 3 similar" in page

    response = client.post(
        "/labels",
        data=label_form(similar[0], groceries, tag_1="Weekly", scope="similar"),
    )

    assert response.status_code == 303
    labels = [stored(session, operation) for operation in similar]
    assert [label.category_id for label in labels] == [groceries.id] * 3
    assert [label.tags for label in labels] == [["Weekly"]] * 3
    assert stored(session, different) is None


def test_save_for_all_similar_stays_within_the_filter(
    client, session, add_operation, groceries
):
    october = add_operation(date(2026, 10, 1))
    september = add_operation(date(2026, 9, 1))

    client.post(
        "/labels",
        data=label_form(october, groceries, month="2026-10", scope="similar"),
    )

    assert stored(session, october) is not None
    assert stored(session, september) is None


def test_month_filter_narrows_the_queue_and_is_kept_after_saving(
    client, add_operation, groceries
):
    add_operation(date(2026, 9, 30))
    first = add_operation(date(2026, 10, 1), OTHER)
    add_operation(date(2026, 10, 31))

    page = queue(client, first, month="2026-10").text
    assert "2 to label" in page
    assert shown_operation_id(page) == first.id

    response = client.post(
        "/labels", data=label_form(first, groceries, month="2026-10")
    )

    assert response.headers["location"] == (
        f"/labels/new?account_id={first.account_id}&month=2026-10"
    )
    assert "1 to label" in client.get(response.headers["location"]).text


def test_account_filter_narrows_the_queue(
    client, session, bank, add_operation, groceries
):
    other_account = AccountModel(
        name="Other label account",
        bank=bank,
        type=AccountType.SAVINGS,
        opened_on=date(2020, 1, 15),
    )
    session.add(other_account)
    session.commit()
    mine = add_operation(date(2026, 10, 1))
    add_operation(date(2026, 9, 1), target=other_account)

    page = queue(client, mine).text

    assert "1 to label" in page
    assert shown_operation_id(page) == mine.id


@pytest.mark.parametrize("month", ["2026-13", "10/2026", "2026-1"])
def test_invalid_month_filter_is_rejected(client, add_operation, month):
    response = queue(client, add_operation(date(2026, 10, 1)), month=month)

    assert response.status_code == 422


def test_note_and_tags_are_stored_cleaned(client, session, add_operation, groceries):
    current = add_operation(date(2026, 11, 2))

    client.post(
        "/labels",
        data=label_form(
            current,
            groceries,
            tag_1=" Holiday ",
            tag_2="",
            tag_3="Holiday",
            note="  Shared with Alex  ",
        ),
    )

    label = stored(session, current)
    assert label.tags == ["Holiday"]
    assert label.note == "Shared with Alex"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"category_id": ""}, "valid integer"),
        ({"tag_2": "x" * 51}, "at most 50 characters"),
        ({"note": "x" * 501}, "at most 500 characters"),
        ({"category_id": str(MAX_ID)}, "This category no longer exists."),
    ],
)
def test_invalid_label_is_rejected_and_nothing_written(
    client, session, add_operation, groceries, overrides, message
):
    current = add_operation(date(2026, 11, 2))

    response = client.post("/labels", data=label_form(current, groceries, **overrides))

    assert response.status_code == 422
    assert message in response.text
    assert stored(session, current) is None


def test_labelling_an_unknown_operation_is_not_found(client, groceries, add_operation):
    form = label_form(add_operation(date(2026, 11, 2)), groceries)

    response = client.post("/labels", data=form | {"operation_id": str(MAX_ID)})

    assert response.status_code == 404


def test_labelling_a_labelled_operation_is_a_conflict(
    client, session, add_operation, groceries, leisure
):
    current = add_operation(date(2026, 11, 2))
    add_label(session, current, leisure)

    response = client.post("/labels", data=label_form(current, groceries))

    assert response.status_code == 409
    assert stored(session, current).category_id == leisure.id


def test_cross_site_label_is_refused(client, session, add_operation, groceries):
    current = add_operation(date(2026, 11, 2))

    response = client.post(
        "/labels",
        data=label_form(current, groceries),
        headers={"Sec-Fetch-Site": "cross-site"},
    )

    assert response.status_code == 403
    assert stored(session, current) is None


def test_queue_without_categories_asks_to_add_one(client, session, add_operation):
    current = add_operation(date(2026, 11, 2))
    # Rolled back after the test, like every write of the test session.
    session.execute(text("DELETE FROM banking.labels"))
    session.execute(text("DELETE FROM banking.categories"))

    page = queue(client, current).text

    assert "add a category</a> first" in page
    assert 'action="/labels"' not in page


def test_account_page_shows_labels(client, session, add_operation, groceries):
    labelled = add_operation(date(2026, 11, 2))
    add_label(session, labelled, groceries, ["Holiday", "Lisbon"])
    unlabelled = add_operation(date(2026, 11, 1), OTHER)

    page = client.get(f"/accounts/{labelled.account_id}").text

    assert "<td>Test groceries</td>" in page
    assert "<td>Holiday, Lisbon</td>" in page
    assert f'href="/labels/{labelled.id}/edit"' in page
    assert f'href="/labels/{unlabelled.id}/edit"' not in page


def test_user_text_is_never_rendered_as_markup(client, session, add_operation):
    category = add_category(session, "<i>Food</i>")
    labelled = add_operation(date(2026, 11, 2))
    add_label(session, labelled, category, ["<b>Bold</b>"])
    add_operation(date(2026, 11, 3))

    pages = [
        client.get(f"/accounts/{labelled.account_id}").text,
        queue(client, labelled).text,
        client.get(f"/labels/{labelled.id}/edit").text,
    ]

    for page in pages:
        assert "<b>Bold</b>" not in page
        assert "<i>Food</i>" not in page
        assert "&lt;b&gt;Bold&lt;/b&gt;" in page


def test_editing_a_label_makes_it_manual(
    client, session, add_operation, groceries, leisure
):
    current = add_operation(date(2026, 11, 2))
    add_label(session, current, leisure, ["Holiday"], LabelSource.SUGGESTION)

    response = client.post(
        f"/labels/{current.id}",
        data={"category_id": str(groceries.id), "tag_1": "Holiday"},
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        f"/accounts/{current.account_id}#operation-{current.id}"
    )
    label = stored(session, current)
    assert (label.category_id, label.source) == (groceries.id, LabelSource.MANUAL)


def test_editing_only_the_note_keeps_the_source(
    client, session, add_operation, leisure
):
    current = add_operation(date(2026, 11, 2))
    add_label(session, current, leisure, ["Holiday"], LabelSource.SUGGESTION)

    client.post(
        f"/labels/{current.id}",
        data={"category_id": str(leisure.id), "tag_1": "Holiday", "note": "Gift"},
    )

    label = stored(session, current)
    assert (label.note, label.source) == ("Gift", LabelSource.SUGGESTION)


def test_edit_page_is_prefilled(client, session, add_operation, leisure):
    current = add_operation(date(2026, 11, 2))
    add_label(session, current, leisure, ["Holiday"])

    page = client.get(f"/labels/{current.id}/edit").text

    assert "<html" in page
    assert f'<option value="{leisure.id}" selected>' in page
    assert 'name="tag_1" value="Holiday"' in page


def test_invalid_edit_is_rejected_and_nothing_written(
    client, session, add_operation, leisure
):
    current = add_operation(date(2026, 11, 2))
    add_label(session, current, leisure, ["Holiday"])

    response = client.post(
        f"/labels/{current.id}",
        data={"category_id": str(leisure.id), "note": "x" * 501},
    )

    assert response.status_code == 422
    assert "<html" in response.text
    assert stored(session, current).note is None


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", f"/labels/{MAX_ID}/edit"),
        ("post", f"/labels/{MAX_ID}"),
        ("get", f"/labels/{MAX_ID}"),
    ],
)
def test_unknown_label_is_not_found(client, groceries, method, path):
    data = {"data": {"category_id": str(groceries.id)}} if method == "post" else {}

    assert getattr(client, method)(path, **data).status_code == 404


def test_htmx_edit_returns_the_row_as_a_form(client, session, add_operation, leisure):
    current = add_operation(date(2026, 11, 2))
    add_label(session, current, leisure, ["Holiday"])

    response = client.get(f"/labels/{current.id}/edit", headers=HTMX)

    assert response.status_code == 200
    assert response.text.lstrip().startswith(f'<tr id="operation-{current.id}">')
    assert "<html" not in response.text
    assert '<select name="category_id" required autofocus>' in response.text
    assert response.headers["vary"] == "HX-Request"


def test_htmx_save_returns_the_updated_row(
    client, session, add_operation, groceries, leisure
):
    current = add_operation(date(2026, 11, 2))
    add_label(session, current, leisure)

    response = client.post(
        f"/labels/{current.id}",
        data={"category_id": str(groceries.id), "tag_1": "Weekly"},
        headers=HTMX,
    )

    assert response.status_code == 200
    assert "<html" not in response.text
    assert "<td>Test groceries</td>" in response.text
    assert "<td>Weekly</td>" in response.text
    # Focus goes back to the row's Edit link.
    assert "autofocus>Edit label</a>" in response.text


def test_htmx_invalid_save_returns_the_form_row_with_the_error(
    client, session, add_operation, leisure
):
    current = add_operation(date(2026, 11, 2))
    add_label(session, current, leisure)

    response = client.post(
        f"/labels/{current.id}",
        data={"category_id": str(leisure.id), "tag_1": "x" * 51},
        headers=HTMX,
    )

    assert response.status_code == 422
    assert "<html" not in response.text
    assert "at most 50 characters" in response.text


def test_cancel_returns_the_row_or_goes_back_to_the_account(
    client, session, add_operation, leisure
):
    current = add_operation(date(2026, 11, 2))
    add_label(session, current, leisure)

    row = client.get(f"/labels/{current.id}", headers=HTMX)
    page = client.get(f"/labels/{current.id}")

    assert row.status_code == 200
    assert "<td>Test leisure</td>" in row.text
    assert "<html" not in row.text
    assert page.status_code == 303
    assert page.headers["location"] == (
        f"/accounts/{current.account_id}#operation-{current.id}"
    )


def test_merging_categories_keeps_the_labels(
    client, session, add_operation, groceries, leisure
):
    current = add_operation(date(2026, 11, 2))
    client.post("/labels", data=label_form(current, groceries))

    client.post(f"/categories/{groceries.id}/merge", data={"into_id": str(leisure.id)})

    assert stored(session, current).category_id == leisure.id


def test_deleting_an_account_deletes_its_labels(
    client, session, add_operation, groceries
):
    current = add_operation(date(2026, 11, 2))
    client.post("/labels", data=label_form(current, groceries))

    operation_id = current.id

    client.post(f"/accounts/{current.account_id}/delete")

    session.expire_all()
    assert session.get(LabelModel, operation_id) is None


def test_htmx_is_served_by_the_app(client):
    page = client.get("/labels/new").text
    path = re.search(r'<script src="(/static/htmx-[\d.]+\.min\.js)" defer>', page)[1]

    response = client.get(path)

    assert response.status_code == 200
    assert "htmx" in response.text
