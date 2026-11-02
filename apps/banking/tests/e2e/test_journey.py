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

        # Label one copy by hand in the operations table, then accept last time's
        # category for the other.
        assert client.post("/categories", data={"name": category}).status_code == 303
        category_id = re.search(
            rf'<td>{category}</td>.*?href="/categories/(\d+)/edit"',
            client.get("/categories").text,
            re.DOTALL,
        )[1]
        account_id = account_url.rsplit("/", 1)[1]
        filters = {"account": account_id, "labelled": "no"}
        page = client.get("/operations", params=filters).text
        first, second = operation_ids(page, "CB E2E SHOP")
        assert len(operation_ids(page)) == 3
        assert 'name="only"' not in page
        response = client.post(
            "/labels", data=filters | {"id": first, "category_id": category_id}
        )
        assert response.status_code == 303
        page = client.get(response.headers["location"]).text
        assert "1 operation labelled." in page
        assert operation_ids(page, "CB E2E SHOP") == [second]
        response = client.post("/labels/accept", data=filters | {"only": second})
        assert response.status_code == 303
        page = client.get(response.headers["location"]).text
        assert "1 suggestion accepted." in page
        assert len(operation_ids(page)) == 1
        labelled = client.get(
            "/operations", params={"account": account_id, "category": category_id}
        ).text
        assert len(operation_ids(labelled)) == 2

        # Cleaning up is part of the journey: the account (and its labels), then the
        # now unused category and bank.
        assert client.post(f"{account_url}/delete").status_code == 303
        assert account not in client.get("/accounts").text
        assert client.post(f"/categories/{category_id}/delete").status_code == 303
        assert client.post(f"/banks/{bank_id}/delete").status_code == 303
        assert bank not in client.get("/banks").text


def operation_ids(page: str, description: str = "") -> list[str]:
    """The ids of the table's rows whose description starts with this text."""
    return re.findall(
        rf'name="id" value="(\d+)"[^>]*aria-label="Select \S+ {re.escape(description)}',
        page,
    )
