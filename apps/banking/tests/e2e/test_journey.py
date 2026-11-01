"""Main user journey on the running stack: `docker compose up -d --wait banking-web`."""

import os
import re
from uuid import uuid4

import httpx

BASE_URL = os.environ.get("BANKING_E2E_URL", "http://127.0.0.1:8000")


def test_declare_then_delete_a_bank_and_an_account():
    # Unique names: the running stack's database outlives the test.
    bank, account = f"E2E bank {uuid4().hex[:8]}", f"E2E {uuid4().hex[:8]}"
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
                "opened_on": "2024-01-01",
            },
        )
        assert response.status_code == 303
        account_url = response.headers["location"]
        page = client.get(account_url).text
        assert account in page
        assert bank in page
        assert account in client.get("/").text

        # Cleaning up is part of the journey: the account, then its now unused bank.
        assert client.post(f"{account_url}/delete").status_code == 303
        assert account not in client.get("/").text
        assert client.post(f"/banks/{bank_id}/delete").status_code == 303
        assert bank not in client.get("/banks").text
