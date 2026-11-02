import re
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from banking.databases.models import (
    AccountModel,
    CategoryModel,
    ImportModel,
    LabelModel,
    OperationModel,
)
from banking.domains.account import AccountType

MAX_ID = 2**31 - 1  # largest INTEGER


# The local database also holds seed data: compare counts, don't expect an empty table.
def count_categories(session):
    return session.scalar(select(func.count()).select_from(CategoryModel))


def add_category(session, name):
    category = CategoryModel(name=name)
    session.add(category)
    session.commit()
    return category


@pytest.fixture
def category(session):
    return add_category(session, "Test groceries")


@pytest.fixture
def other(session):
    return add_category(session, "Test food")


@pytest.fixture
def label(session, bank):
    """Label an operation with a category; return the label."""
    account = AccountModel(
        name="Main account",
        bank=bank,
        type=AccountType.CURRENT,
        opened_on=date(2020, 1, 15),
    )
    session.add(account)
    session.flush()
    imported = ImportModel(
        account_id=account.id,
        export_date=date(2026, 10, 31),
        balance=Decimal("100.00"),
        rows_in_file=0,
        rows_new=0,
    )
    session.add(imported)
    session.flush()
    created = 0

    def make(category):
        nonlocal created
        created += 1
        operation = OperationModel(
            account_id=account.id,
            import_id=imported.id,
            operation_date=date(2026, 10, created),
            description="CB SHOP",
            amount=Decimal("-9.99"),
            occurrence=1,
        )
        session.add(operation)
        session.flush()
        label = LabelModel(
            operation_id=operation.id,
            category_id=category.id,
        )
        session.add(label)
        session.commit()
        return label

    return make


def category_ids(session, labels):
    session.expire_all()
    return [session.get(LabelModel, label.operation_id).category_id for label in labels]


def test_added_category_is_listed(client):
    response = client.post("/categories", data={"name": "  Test leisure  "})

    assert response.status_code == 303
    assert "<td>Test leisure</td>" in client.get("/categories").text


@pytest.mark.parametrize(
    ("name", "message"),
    [
        (" ", "at least 1 character"),
        ("x" * 51, "at most 50 characters"),
        ("Test groceries", "Another category already has this name."),
    ],
)
def test_invalid_or_duplicate_name_is_rejected_and_nothing_written(
    client, session, category, name, message
):
    before = count_categories(session)

    response = client.post("/categories", data={"name": name})

    assert response.status_code == 422
    assert message in response.text
    assert count_categories(session) == before


def test_category_name_is_never_rendered_as_markup(client):
    client.post("/categories", data={"name": "<b>Bold</b>"})

    page = client.get("/categories").text

    assert "&lt;b&gt;Bold&lt;/b&gt;" in page
    assert "<b>Bold</b>" not in page


def test_rename_keeps_the_labels(client, session, category, label):
    labelled = label(category)
    assert (
        'value="Test groceries"' in client.get(f"/categories/{category.id}/edit").text
    )

    response = client.post(f"/categories/{category.id}", data={"name": "Test shopping"})

    assert response.status_code == 303
    page = client.get("/categories").text
    assert "Test shopping" in page
    assert "Test groceries" not in page
    assert category_ids(session, [labelled]) == [category.id]


def test_rename_to_a_taken_name_is_rejected(client, category, other):
    response = client.post(f"/categories/{other.id}", data={"name": "Test groceries"})

    assert response.status_code == 422
    assert "Another category already has this name." in response.text


def test_unused_category_can_be_deleted(client, session, category):
    before = count_categories(session)

    response = client.post(f"/categories/{category.id}/delete")

    assert response.status_code == 303
    assert count_categories(session) == before - 1


def test_category_in_use_cannot_be_deleted(client, session, category, label):
    labelled = label(category)
    before = count_categories(session)

    response = client.post(f"/categories/{category.id}/delete")

    assert response.status_code == 409
    assert "Labels still use this category" in response.text
    assert count_categories(session) == before
    assert category_ids(session, [labelled]) == [category.id]


def test_list_counts_labels(client, category, label):
    label(category)
    label(category)

    page = re.sub(r"\s+", " ", client.get("/categories").text)

    assert '<td>Test groceries</td> <td class="num">2</td>' in page


def test_merge_moves_every_label_and_removes_the_category(
    client, session, category, other, label
):
    labels = [label(category), label(category), label(other)]
    before = count_categories(session)

    response = client.post(
        f"/categories/{category.id}/merge", data={"into_id": str(other.id)}
    )

    assert response.status_code == 303
    assert category_ids(session, labels) == [other.id] * 3
    assert count_categories(session) == before - 1
    assert session.get(CategoryModel, category.id) is None


@pytest.mark.parametrize(
    ("into", "message"),
    [
        ("self", "Pick another category to merge into."),
        (str(MAX_ID), "This category no longer exists."),
        ("", "valid integer"),
    ],
)
def test_invalid_merge_is_rejected_and_nothing_written(
    client, session, category, label, into, message
):
    labelled = label(category)
    into_id = str(category.id) if into == "self" else into

    response = client.post(
        f"/categories/{category.id}/merge", data={"into_id": into_id}
    )

    assert response.status_code == 422
    assert message in response.text
    assert category_ids(session, [labelled]) == [category.id]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", f"/categories/{MAX_ID}/edit"),
        ("post", f"/categories/{MAX_ID}"),
        ("post", f"/categories/{MAX_ID}/merge"),
        ("post", f"/categories/{MAX_ID}/delete"),
    ],
)
def test_unknown_category_is_not_found(client, category, method, path):
    data = (
        {"data": {"name": "x", "into_id": str(category.id)}} if method == "post" else {}
    )

    assert getattr(client, method)(path, **data).status_code == 404


def test_cross_site_merge_is_refused(client, session, category, other):
    response = client.post(
        f"/categories/{category.id}/merge",
        data={"into_id": str(other.id)},
        headers={"Sec-Fetch-Site": "cross-site"},
    )

    assert response.status_code == 403
    assert session.get(CategoryModel, category.id) is not None


def test_database_refuses_to_delete_a_category_in_use(session, category, label):
    # Other writers will skip the web app: the foreign key must refuse.
    label(category)

    with pytest.raises(IntegrityError):
        session.execute(
            text("DELETE FROM banking.categories WHERE id = :id"), {"id": category.id}
        )


def test_deleting_an_operation_deletes_its_label(session, category, label):
    labelled = label(category)

    session.execute(
        text("DELETE FROM banking.operations WHERE id = :id"),
        {"id": labelled.operation_id},
    )

    assert (
        session.scalar(
            text("SELECT count(*) FROM banking.labels WHERE operation_id = :id"),
            {"id": labelled.operation_id},
        )
        == 0
    )
