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
        assert client.post("/banks", data={"name": bank}).status_code == 303
        bank_id = re.search(
            rf'<td>{bank}</td>.*?action="/banks/(\d+)/delete"',
            client.get("/banks").text,
            re.DOTALL,
        )[1]

        response = client.post(
            "/accounts",
            data={
                "name": account,
                "bank_id": bank_id,
                "type": "current",
                "account_number": number,
                "opened_on": "2024-01-01",
            },
        )
        assert response.status_code == 303
        account_url = response.headers["location"]
        page = client.get(account_url).text
        assert account in page
        assert bank in page
        assert "Never imported" in page

        response = client.post(
            f"{account_url}/imports", files={"file": ("export.csv", export)}
        )
        assert response.status_code == 303
        page = client.get(response.headers["location"]).text
        assert "3 rows in the file: 3 new, 0 already known." in page
        assert "File dated 2 days ago" in page
        assert page.count("CB E2E SHOP") == 2

        # Label the first operation by hand: its identical copy gets the suggestion.
        assert client.post("/categories", data={"name": category}).status_code == 303
        category_id = re.search(
            rf'<td>{category}</td>.*?href="/categories/(\d+)/edit"',
            client.get("/categories").text,
            re.DOTALL,
        )[1]
        queue_url = f"/labels/new?account_id={account_url.rsplit('/', 1)[1]}"
        page = client.get(queue_url).text
        assert "3 to label" in page
        assert "Suggested from" not in page
        label = {
            "operation_id": operation_id(page),
            "account_id": account_url.rsplit("/", 1)[1],
            "category_id": category_id,
        }
        assert client.post("/labels", data=label).status_code == 303
        page = client.get(queue_url).text
        assert "2 to label" in page
        assert f"Suggested from the operation of {today - timedelta(days=3)}." in page
        response = client.post(
            "/labels", data=label | {"operation_id": operation_id(page)}
        )
        assert response.status_code == 303
        assert "1 to label" in client.get(queue_url).text
        assert client.get(account_url).text.count(f"<td>{category}</td>") == 2

        # Cleaning up is part of the journey: the account (and its labels), then the
        # now unused category and bank.
        assert client.post(f"{account_url}/delete").status_code == 303
        assert account not in client.get("/accounts").text
        assert client.post(f"/categories/{category_id}/delete").status_code == 303
        assert client.post(f"/banks/{bank_id}/delete").status_code == 303
        assert bank not in client.get("/banks").text


def operation_id(page: str) -> str:
    """The id of the operation the queue page shows."""
    return re.search(r'name="operation_id" value="(\d+)"', page)[1]
