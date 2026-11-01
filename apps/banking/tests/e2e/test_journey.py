"""Main user journey on the running stack: `docker compose up -d --wait banking-web`."""

import os
from uuid import uuid4

import httpx

BASE_URL = os.environ.get("BANKING_E2E_URL", "http://127.0.0.1:8000")


def test_declare_an_account():
    # A unique name: the running stack's database outlives the test.
    name = f"E2E {uuid4().hex[:8]}"
    with httpx.Client(base_url=BASE_URL) as client:
        response = client.post(
            "/accounts",
            data={
                "name": name,
                "bank": "banque_postale",
                "type": "current",
                "opened_on": "2024-01-01",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert name in response.text
        assert name in client.get("/").text
