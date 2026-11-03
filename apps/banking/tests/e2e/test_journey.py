"""Main user journey on the running stack: `docker compose up -d --wait banking-web`."""

import os
import re
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import httpx

from banking.domains.operation import OperationFields
from banking.tools.fakes import build_export

BASE_URL = os.environ.get("BANKING_E2E_URL", "http://127.0.0.1:8000")


def test_declare_an_account_import_label_its_operations_then_delete_it():
    # Unique names: the running stack's database outlives the test.
    suffix = uuid4().hex[:8]
    bank, account, number = f"E2E bank {suffix}", f"E2E {suffix}", suffix.upper()
    category = f"E2E category {suffix}"
    today = date.today()
    operations = [
        OperationFields(today - timedelta(days=3), "CB E2E SHOP", Decimal("-9.99")),
        OperationFields(today - timedelta(days=3), "CB E2E SHOP", Decimal("-9.99")),
        OperationFields(today - timedelta(days=1), "VIREMENT E2E", Decimal("100.00")),
    ]
    export = build_export(number, today - timedelta(days=2), operations)

    with httpx.Client(base_url=BASE_URL) as client:
        # The bank, the category and the account are declared in the admin.
        client.get("/admin/banks/list")
        token = client.cookies["starlette_admin_csrftoken"]
        client.headers["X-CSRFToken"] = token
        for view, name in (("banks", bank), ("categories", category)):
            response = client.post(f"/admin/{view}/create", data={"name": name})
            assert response.status_code == 303
        bank_id = admin_id(client, "banks", bank)
        response = client.post(
            "/admin/accounts/create",
            data={
                "name": account,
                "bank": bank_id,
                "type": "current",
                "account_number": number,
                "opened_on": "2024-01-01",
            },
        )
        assert response.status_code == 303
        account_id = admin_id(client, "accounts", account)

        # The Import page lists it as never imported; a file is imported there.
        assert client.get("/").headers["location"] == "/imports"
        account_url = f"/imports?account_id={account_id}"
        page = client.get(account_url).text
        assert account in page
        assert bank in page
        assert "Never imported" in page

        response = client.post(
            f"/accounts/{account_id}/imports", files={"file": ("export.csv", export)}
        )
        assert response.status_code == 303
        page = client.get(response.headers["location"]).text
        assert "3 rows in the file: 3 new, 0 already known." in page
        assert "File dated 2 days ago" in page

        # The recap links each month's unlabelled operations to the admin's table:
        # label them all at once there.
        links = [
            link.replace("&amp;", "&")
            for link in re.findall(r'href="(/admin/operations/list\?[^"]+)"', page)
            if "category__is_null" in link
        ]
        assert links
        category_id = admin_id(client, "categories", category)
        for link in links:
            response = client.post(
                "/admin/_api/operations/action",
                params={
                    "name": "set_category",
                    "all": "1",
                    "_list_query": link.split("?", 1)[1],
                },
                data={"category_id": category_id},
            )
            assert response.status_code == 200
        assert "category__is_null" not in client.get(account_url).text

        # Cleaning up is part of the journey, in the admin: the account (and its
        # history), then the now unused category and bank.
        for view, item_id in (
            ("accounts", account_id),
            ("categories", category_id),
            ("banks", bank_id),
        ):
            response = client.post(
                f"/admin/_api/{view}/action", params={"name": "delete", "pks": item_id}
            )
            assert response.status_code == 200
        assert account not in client.get("/imports").text
        banks = client.get("/admin/banks/list", params={"q": bank}).text
        assert "data-sa-pk" not in banks


def admin_id(client, view, name):
    """The id of the record with this name in an admin list."""
    page = client.get(f"/admin/{view}/list", params={"q": name}).text
    return re.search(rf'data-sa-pk="(\d+)"(?:(?!data-sa-pk).)*?>{name}<', page, re.S)[1]
