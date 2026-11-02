"""Editing one label in place, from the account page."""

import re
from datetime import date

import pytest

from banking.api.schemas.common import MAX_ID

HTMX = {"HX-Request": "true"}


def test_account_page_shows_labels(client, add_operation, groceries, add_label):
    labelled = add_operation(date(2026, 11, 2))
    add_label(labelled, groceries)
    unlabelled = add_operation(date(2026, 11, 1), "other")

    page = re.sub(r"\s+", " ", client.get(f"/accounts/{labelled.account_id}").text)

    assert "<td>Test groceries</td>" in page
    assert re.search(rf'href="/labels/{labelled.id}/edit"[^>]*>Edit label<', page)
    assert re.search(rf'href="/labels/{unlabelled.id}/edit"[^>]*>Add label<', page)


def test_unlabelled_operation_is_labelled_in_place(
    client, add_operation, groceries, stored
):
    current = add_operation(date(2026, 11, 2))

    form = client.get(f"/labels/{current.id}/edit", headers=HTMX)
    response = client.post(
        f"/labels/{current.id}",
        data={"category_id": str(groceries.id)},
        headers=HTMX,
    )

    assert form.status_code == 200
    assert form.text.lstrip().startswith(f'<tr id="operation-{current.id}">')
    assert " selected>" not in form.text
    assert response.status_code == 200
    assert "<td>Test groceries</td>" in response.text
    assert "autofocus>Edit label</a>" in response.text
    assert stored(current).category_id == groceries.id


def test_add_label_page_suggests_nothing(
    client, add_operation, leisure, add_label, stored
):
    add_label(add_operation(date(2026, 10, 28)), leisure)
    current = add_operation(date(2026, 11, 2))

    page = client.get(f"/labels/{current.id}/edit").text
    response = client.post(
        f"/labels/{current.id}",
        data={"category_id": str(leisure.id)},
    )

    assert "<h1>Add label</h1>" in page
    assert " selected>" not in page
    assert response.status_code == 303
    assert response.headers["location"] == (
        f"/accounts/{current.account_id}#operation-{current.id}"
    )
    assert stored(current).category_id == leisure.id


def test_invalid_new_label_is_rejected_and_nothing_written(
    client, add_operation, stored
):
    current = add_operation(date(2026, 11, 2))

    response = client.post(
        f"/labels/{current.id}", data={"category_id": str(MAX_ID)}, headers=HTMX
    )

    assert response.status_code == 422
    assert "This category no longer exists." in response.text
    assert stored(current) is None


def test_user_text_is_never_rendered_as_markup(
    client, add_operation, add_label, add_category
):
    category = add_category("<i>Food</i>")
    labelled = add_operation(date(2026, 11, 2))
    add_label(labelled, category)
    add_operation(date(2026, 11, 3))

    pages = [
        client.get(f"/accounts/{labelled.account_id}").text,
        client.get(f"/labels/{labelled.id}/edit").text,
    ]

    for page in pages:
        assert "<i>Food</i>" not in page
        assert "&lt;i&gt;Food&lt;/i&gt;" in page


def test_editing_a_label_changes_its_category(
    client, add_operation, groceries, leisure, add_label, stored
):
    current = add_operation(date(2026, 11, 2))
    add_label(current, leisure)

    response = client.post(
        f"/labels/{current.id}",
        data={"category_id": str(groceries.id)},
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        f"/accounts/{current.account_id}#operation-{current.id}"
    )
    assert stored(current).category_id == groceries.id


def test_edit_page_is_prefilled(client, add_operation, leisure, add_label):
    current = add_operation(date(2026, 11, 2))
    add_label(current, leisure)

    page = client.get(f"/labels/{current.id}/edit").text

    assert "<html" in page
    assert f'<option value="{leisure.id}" selected>' in page


def test_invalid_edit_is_rejected_and_nothing_written(
    client, add_operation, leisure, add_label, stored
):
    current = add_operation(date(2026, 11, 2))
    add_label(current, leisure)

    response = client.post(
        f"/labels/{current.id}",
        data={"category_id": ""},
    )

    assert response.status_code == 422
    assert "<html" in response.text
    assert stored(current).category_id == leisure.id


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", f"/labels/{MAX_ID}/edit"),
        ("post", f"/labels/{MAX_ID}"),
        ("get", f"/labels/{MAX_ID}"),
    ],
)
def test_unknown_operation_is_not_found(client, groceries, method, path):
    data = {"data": {"category_id": str(groceries.id)}} if method == "post" else {}

    assert getattr(client, method)(path, **data).status_code == 404


def test_htmx_edit_returns_the_row_as_a_form(client, add_operation, leisure, add_label):
    current = add_operation(date(2026, 11, 2))
    add_label(current, leisure)

    response = client.get(f"/labels/{current.id}/edit", headers=HTMX)

    assert response.status_code == 200
    assert response.text.lstrip().startswith(f'<tr id="operation-{current.id}">')
    assert "<html" not in response.text
    assert '<select name="category_id" required autofocus>' in response.text
    assert response.headers["vary"] == "HX-Request"


def test_htmx_save_returns_the_updated_row(
    client, add_operation, groceries, leisure, add_label
):
    current = add_operation(date(2026, 11, 2))
    add_label(current, leisure)

    response = client.post(
        f"/labels/{current.id}",
        data={"category_id": str(groceries.id)},
        headers=HTMX,
    )

    assert response.status_code == 200
    assert "<html" not in response.text
    assert "<td>Test groceries</td>" in response.text
    # Focus goes back to the row's Edit link.
    assert "autofocus>Edit label</a>" in response.text


def test_htmx_invalid_save_returns_the_form_row_with_the_error(
    client, add_operation, leisure, add_label
):
    current = add_operation(date(2026, 11, 2))
    add_label(current, leisure)

    response = client.post(
        f"/labels/{current.id}",
        data={"category_id": ""},
        headers=HTMX,
    )

    assert response.status_code == 422
    assert "<html" not in response.text
    assert "valid integer" in response.text


def test_cancel_returns_the_row_or_goes_back_to_the_account(
    client, add_operation, leisure, add_label
):
    current = add_operation(date(2026, 11, 2))
    add_label(current, leisure)

    row = client.get(f"/labels/{current.id}", headers=HTMX)
    page = client.get(f"/labels/{current.id}")

    assert row.status_code == 200
    assert "<td>Test leisure</td>" in row.text
    assert "<html" not in row.text
    assert page.status_code == 303
    assert page.headers["location"] == (
        f"/accounts/{current.account_id}#operation-{current.id}"
    )


def test_cancel_on_an_unlabelled_operation_returns_its_row(client, add_operation):
    current = add_operation(date(2026, 11, 2))

    row = client.get(f"/labels/{current.id}", headers=HTMX)

    assert row.status_code == 200
    assert "Add label</a>" in row.text


def test_htmx_is_served_by_the_app(client):
    page = client.get("/operations").text
    path = re.search(r'<script src="(/static/htmx-[\d.]+\.min\.js)" defer>', page)[1]

    response = client.get(path)

    assert response.status_code == 200
    assert "htmx" in response.text
