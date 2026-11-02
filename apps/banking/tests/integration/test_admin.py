"""The admin: label operations, edit categories and banks, within the constraints."""

import re
from datetime import date
from decimal import Decimal
from urllib.parse import urlencode

import pytest
from sqlalchemy import select

from banking.databases.models import BankModel, CategoryModel, OperationModel


@pytest.fixture
def admin(client):
    """The client, holding the admin's CSRF cookie; posts send the token back."""
    client.get("/admin/operations/list")
    token = client.cookies["starlette_admin_csrftoken"]
    client.headers["X-CSRFToken"] = token
    return client


def action(admin, view, name, data=None, pks=(), filters=None):
    """Run a bulk action on rows (by id), or on every row the filters keep."""
    params = {"name": name}
    if filters is None:
        params["pks"] = [str(pk) for pk in pks]
    else:
        params |= {"all": "1", "_list_query": "?" + urlencode({"filter": filters})}
    return admin.post(f"/admin/_api/{view}/action", params=params, data=data or {})


def listed_ids(admin, filters):
    page = admin.get("/admin/operations/list", params={"filter": filters})
    assert page.status_code == 200
    return [int(pk) for pk in re.findall(r'<tr data-sa-pk="(\d+)"', page.text)]


def test_inline_edit_sets_an_operations_category(
    admin, add_operation, groceries, category_of
):
    operation = add_operation(date(2026, 10, 1))

    response = admin.post(
        "/admin/_api/operations/inline-edit",
        params={"pk": operation.id, "field": "category"},
        data={"category": str(groceries.id)},
    )

    assert response.status_code == 200
    assert category_of(operation) == groceries.id


def test_set_category_labels_every_operation_the_filters_keep(
    admin, account, add_account, add_operation, groceries, leisure, category_of
):
    unlabelled = [add_operation(date(2026, 10, day)) for day in (1, 2)]
    labelled = add_operation(date(2026, 10, 3), category=leisure)
    elsewhere = add_operation(date(2026, 10, 1), target=add_account("Other"))

    response = action(
        admin,
        "operations",
        "set_category",
        {"category_id": str(groceries.id)},
        filters=f"account__in={account.id} AND category__is_null",
    )

    assert response.status_code == 200
    assert [category_of(op) for op in unlabelled] == [groceries.id, groceries.id]
    assert category_of(labelled) == leisure.id
    assert category_of(elsewhere) is None


def test_remove_category_unlabels_the_selected_operations(
    admin, add_operation, groceries, category_of
):
    selected, kept = (
        add_operation(date(2026, 10, day), category=groceries) for day in (1, 2)
    )

    response = action(admin, "operations", "remove_category", pks=[selected.id])

    assert response.status_code == 200
    assert category_of(selected) is None
    assert category_of(kept) == groceries.id


def test_set_category_refuses_an_unknown_category(admin, add_operation, category_of):
    operation = add_operation(date(2026, 10, 1))

    response = action(
        admin, "operations", "set_category", {"category_id": "999999"}, [operation.id]
    )

    assert response.status_code == 400
    assert category_of(operation) is None


def test_the_banks_text_of_an_operation_cant_be_edited(
    admin, session, add_operation, groceries
):
    operation = add_operation(date(2026, 10, 1))

    admin.post(
        "/admin/operations/edit",
        params={"pk": operation.id},
        data={
            "csrftoken": admin.headers["X-CSRFToken"],
            "description": "EDITED",
            "amount": "1000",
            "category": str(groceries.id),
        },
    )

    session.expire_all()
    stored = session.get(OperationModel, operation.id)
    assert (stored.description, stored.amount) == (
        "CB LABELTEST SHOP",
        Decimal("-9.99"),
    )
    assert stored.category_id == groceries.id


def test_operations_filter_on_accounts_and_categories(
    admin, account, add_account, add_operation, groceries
):
    mine = add_operation(date(2026, 10, 1), category=groceries)
    add_operation(date(2026, 10, 2))
    add_operation(date(2026, 10, 1), target=add_account("Other"), category=groceries)

    assert listed_ids(
        admin, f"account__in={account.id} AND category__in={groceries.id}"
    ) == [mine.id]


@pytest.mark.parametrize("value", ["0", "x", str(2**31), ""])
def test_operations_filter_refuses_an_invalid_id(admin, value):
    response = admin.get(
        "/admin/operations/list", params={"filter": f"category__in={value}"}
    )

    assert response.status_code == 400


def test_merge_moves_the_operations_then_deletes_the_categories(
    admin, session, add_operation, add_category, groceries, category_of
):
    sources = [add_category("Food"), add_category("Supermarket")]
    operations = [
        add_operation(date(2026, 10, day), category=category)
        for day, category in enumerate(sources, start=1)
    ]

    response = action(
        admin,
        "categories",
        "merge",
        {"target_id": str(groceries.id)},
        [c.id for c in [*sources, groceries]],
    )

    assert response.status_code == 200
    assert [category_of(op) for op in operations] == [groceries.id, groceries.id]
    names = set(session.scalars(select(CategoryModel.name)))
    assert "Test groceries" in names
    assert not names & {"Food", "Supermarket"}


def test_a_category_in_use_cant_be_deleted(admin, session, add_operation, groceries):
    add_operation(date(2026, 10, 1), category=groceries)

    response = action(admin, "categories", "delete", pks=[groceries.id])

    assert response.status_code == 400
    assert "merge it" in response.json()["msg"]
    session.expire_all()
    assert session.get(CategoryModel, groceries.id) is not None


def test_a_bank_an_account_uses_cant_be_deleted(admin, session, account, bank):
    response = action(admin, "banks", "delete", pks=[bank.id])

    assert response.status_code == 400
    session.expire_all()
    assert session.get(BankModel, bank.id) is not None


def test_a_duplicate_name_is_shown_on_its_field(admin, groceries):
    response = admin.post(
        "/admin/categories/create",
        data={"csrftoken": admin.headers["X-CSRFToken"], "name": "Test groceries"},
    )

    assert response.status_code == 422
    assert "Another category already has this name." in response.text


def test_admin_refuses_a_cross_site_post(admin, groceries):
    response = admin.post(
        "/admin/_api/categories/action",
        params={"name": "delete", "pks": [str(groceries.id)]},
        headers={"sec-fetch-site": "cross-site"},
    )

    assert response.status_code == 403
