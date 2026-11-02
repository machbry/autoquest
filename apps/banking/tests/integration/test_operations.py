"""The operations table: filters, sort, selection and the bulk label actions."""

import re
import time
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import insert, select

from banking.api.schemas.common import MAX_ID
from banking.databases.models import (
    BankModel,
    CategoryModel,
    OperationModel,
)


def row_ids(page):
    """The ids of the table's rows, in order."""
    return [int(id_) for id_ in re.findall(r'name="id" value="(\d+)"', page)]


def ticked_ids(page):
    return {int(id_) for id_ in re.findall(r'name="id" value="(\d+)" checked', page)}


def ids(*operations):
    return [operation.id for operation in operations]


def table(client, account, **params):
    """The table, narrowed to the account (the local database holds seed data)."""
    return client.get("/operations", params={"account": account.id, **params})


def action(account, operations, **fields):
    """A bulk action's form: the ticked operations and the table's filters."""
    return {"account": str(account.id), "id": [str(o.id) for o in operations]} | fields


def test_none_category_shows_the_unlabelled_and_stays_after_an_action(
    client, account, add_operation, add_label, groceries
):
    unlabelled = [add_operation(date(2026, 10, day), "other") for day in (1, 2, 3)]
    for day in (4, 5):
        add_label(add_operation(date(2026, 10, day), "other"), groceries)

    page = table(client, account, category="none").text
    response = client.post(
        "/labels",
        data=action(
            account, unlabelled[:1], category="none", category_id=str(groceries.id)
        ),
    )

    assert sorted(row_ids(page)) == ids(*unlabelled)
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith(f"/operations?account={account.id}&category=none&")
    assert row_ids(client.get(location).text) == ids(unlabelled[2], unlabelled[1])


def test_bank_and_category_filters_combine(
    client, session, account, add_account, add_operation, add_label, groceries, leisure
):
    other_bank = BankModel(name="Other test bank")
    session.add(other_bank)
    session.commit()
    mine, theirs = account, add_account("Other", other_bank)
    kept = add_operation(date(2026, 10, 1), target=mine)
    add_label(kept, groceries)
    add_label(add_operation(date(2026, 10, 2), target=mine), leisure)
    add_label(add_operation(date(2026, 10, 3), target=theirs), groceries)
    add_operation(date(2026, 10, 4), target=mine)

    page = client.get(
        "/operations", params={"bank": mine.bank_id, "category": groceries.id}
    ).text

    assert row_ids(page) == [kept.id]


def test_sorting_by_amount_follows_the_order(client, account, add_operation):
    small = add_operation(date(2026, 10, 1), amount="-50.00")
    large = add_operation(date(2026, 10, 2), amount="1200.00")
    middle = add_operation(date(2026, 10, 3), amount="3.50")

    ascending = table(client, account, sort="amount", order="asc").text
    descending = table(client, account, sort="amount", order="desc").text

    assert row_ids(ascending) == ids(small, middle, large)
    assert row_ids(descending) == ids(large, middle, small)
    assert 'aria-sort="descending"' in descending


def test_default_order_is_newest_first(client, account, add_operation):
    older = add_operation(date(2026, 10, 1))
    newer = add_operation(date(2026, 10, 2))

    assert row_ids(table(client, account).text) == ids(newer, older)


def test_select_similar_ticks_the_matching_rows_shown(
    client, account, add_account, add_operation
):
    hidden_account = add_account("Hidden")
    similar = [add_operation(date(2026, 10, day)) for day in (1, 5, 9, 28)]
    add_operation(date(2026, 10, 2), "other")
    add_operation(date(2026, 10, 3), target=hidden_account)

    page = table(client, account, similar_to=similar[-1].id, id=similar[0].id).text

    assert ticked_ids(page) == set(ids(*similar))
    assert "4 selected" in page


def test_select_all_ticks_every_row_shown(client, account, add_operation):
    operations = [
        add_operation(date(2026, 10, 1), "other"),
        add_operation(date(2026, 10, 2)),
    ]

    page = table(client, account, select="all").text

    assert ticked_ids(page) == set(ids(*operations))
    assert "2 selected" in page


def test_ticked_rows_come_first(client, account, add_operation):
    older, newer = add_operation(date(2026, 10, 1)), add_operation(date(2026, 10, 2))

    page = table(client, account, id=older.id).text

    assert row_ids(page) == ids(older, newer)


def test_setting_a_category_replaces_existing_labels(
    client, account, add_operation, add_label, stored, groceries, leisure
):
    operations = [add_operation(date(2026, 10, day), "other") for day in range(1, 6)]
    add_label(operations[0], leisure)
    add_label(operations[1], leisure)

    response = client.post(
        "/labels", data=action(account, operations, category_id=str(groceries.id))
    )

    assert response.status_code == 303
    assert "notice=set&count=5" in response.headers["location"]
    assert {stored(operation).category_id for operation in operations} == {groceries.id}
    assert "5 operations labelled." in client.get(response.headers["location"]).text


def test_new_category_from_the_picker_labels_the_selection(
    client, session, account, add_operation, stored
):
    operations = [add_operation(date(2026, 10, day)) for day in (1, 2)]

    response = client.post(
        "/labels", data=action(account, operations, new_category="  Test new  ")
    )

    assert response.status_code == 303
    category = session.scalar(
        select(CategoryModel).where(CategoryModel.name == "Test new")
    )
    assert category is not None
    assert {stored(operation).category_id for operation in operations} == {category.id}


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"new_category": "Test groceries"}, "Another category already has this name."),
        ({"new_category": "x" * 51}, "at most 50 characters"),
        ({}, "Choose a category, or name a new one."),
        ({"category_id": "1", "new_category": "Test x"}, "not both"),
        ({"category_id": str(MAX_ID)}, "This category no longer exists."),
    ],
)
def test_invalid_category_is_refused_and_nothing_labelled(
    client, account, add_operation, stored, groceries, fields, message
):
    operation = add_operation(date(2026, 10, 1))

    response = client.post("/labels", data=action(account, [operation], **fields))

    assert response.status_code == 422
    assert message in response.text
    assert stored(operation) is None
    # The table comes back as it was: filtered, the selection still ticked.
    assert row_ids(response.text) == [operation.id]
    assert ticked_ids(response.text) == {operation.id}


def test_removing_the_category_unlabels_the_selection(
    client, account, add_operation, add_label, stored, groceries
):
    operations = [add_operation(date(2026, 10, day)) for day in (1, 2)]
    for operation in operations:
        add_label(operation, groceries)

    response = client.post("/labels/delete", data=action(account, operations))

    assert "notice=removed&count=2" in response.headers["location"]
    assert [stored(operation) for operation in operations] == [None, None]


@pytest.mark.parametrize("path", ["/labels", "/labels/delete"])
def test_an_action_needs_a_selection(client, account, add_operation, groceries, path):
    add_operation(date(2026, 10, 1))

    response = client.post(
        path, data={"account": str(account.id), "category_id": str(groceries.id)}
    )

    assert response.status_code == 422
    assert "Select at least one operation." in response.text


@pytest.mark.parametrize("path", ["/labels", "/labels/delete"])
def test_an_unknown_operation_is_not_found(
    client, account, add_operation, stored, groceries, path
):
    known = add_operation(date(2026, 10, 1))
    data = action(account, [known], category_id=str(groceries.id))
    data["id"].append(str(MAX_ID))

    assert client.post(path, data=data).status_code == 404
    assert stored(known) is None


def test_too_many_operations_are_refused(client, account, add_operation, groceries):
    operation = add_operation(date(2026, 10, 1))
    data = action(account, [operation], category_id=str(groceries.id))
    data["id"] = [str(id_) for id_ in range(1, 502)]

    response = client.post("/labels", data=data)

    assert response.status_code == 422
    assert "at most 500" in response.text


@pytest.mark.parametrize(
    "params",
    [
        {"category": "some"},
        {"sort": "balance"},
        {"order": "up"},
        {"month": "2026-13"},
        {"month": "10/2026"},
        {"bank": ["1", "2"]},
        {"bank": "abc"},
        {"account": str(MAX_ID + 1)},
    ],
)
def test_invalid_query_is_refused(client, params):
    assert client.get("/operations", params=params).status_code == 422


def test_month_filter_keeps_that_month(client, account, add_operation):
    add_operation(date(2026, 9, 30))
    kept = [add_operation(date(2026, 10, day)) for day in (1, 31)]
    add_operation(date(2026, 11, 1))

    page = table(client, account, month="2026-10").text

    assert sorted(row_ids(page)) == ids(*kept)
    assert 'name="month" placeholder="YYYY-MM" value="2026-10"' in page


def test_empty_states(client, account, add_operation, add_label, groceries, leisure):
    add_label(add_operation(date(2026, 10, 1)), groceries)

    assert "Nothing to label." in table(client, account, category="none").text
    assert "No operation matches these filters." in (
        table(client, account, category=leisure.id).text
    )


def test_user_text_is_never_rendered_as_markup(
    client, account, add_operation, add_label, add_category
):
    category = add_category("<i>Food</i>")
    add_label(add_operation(date(2026, 10, 1), "<b>SHOP</b> {:%d%m}"), category)
    add_operation(date(2026, 10, 2), "<b>SHOP</b> {:%d%m}")

    page = table(client, account).text

    assert "<i>Food</i>" not in page
    assert "<b>SHOP</b>" not in page
    assert "&lt;i&gt;Food&lt;/i&gt;" in page
    assert "&lt;b&gt;SHOP&lt;/b&gt;" in page


def test_cross_site_action_is_refused(
    client, account, add_operation, stored, groceries
):
    operation = add_operation(date(2026, 10, 1))

    response = client.post(
        "/labels",
        data=action(account, [operation], category_id=str(groceries.id)),
        headers={"Sec-Fetch-Site": "cross-site"},
    )

    assert response.status_code == 403
    assert stored(operation) is None


def test_two_years_of_operations_answer_within_a_second(
    client, session, account, add_operation, add_label, groceries
):
    first = add_operation(date(2024, 11, 1))
    add_label(first, groceries)
    start = date(2024, 11, 2)
    session.execute(
        insert(OperationModel),
        [
            {
                "account_id": account.id,
                "import_id": session.get(OperationModel, first.id).import_id,
                "operation_date": start + timedelta(days=index % 730),
                "description": f"CB PAYEE{index % 40} {index}",
                "amount": Decimal("-12.34"),
                "occurrence": 1,
            }
            for index in range(2_499)
        ],
    )
    session.commit()

    started = time.perf_counter()
    page = table(client, account).text
    filtered = table(client, account, category="none", sort="amount").text
    elapsed = (time.perf_counter() - started) / 2

    assert len(row_ids(page)) == 2_500
    assert len(row_ids(filtered)) == 2_499
    assert elapsed <= 1
    # Ticking that many at once would exceed what an action takes.
    page = table(client, account, select="all").text
    assert "At most 500 operations at once" in page
    assert not ticked_ids(page)
