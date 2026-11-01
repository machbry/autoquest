"""Pages that several routers render, with the services they show."""

from datetime import date
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse

from banking.api.dependencies.services import (
    AccountServiceDep,
    ImportServiceDep,
    OperationServiceDep,
)
from banking.api.rendering import render


class AccountPage:
    """An account's page: details, freshness, import form and history, operations.

    The account routes and the import route both render it, with their own errors.
    """

    def __init__(
        self,
        accounts: AccountServiceDep,
        imports: ImportServiceDep,
        operations: OperationServiceDep,
    ) -> None:
        """Use the request's services."""
        self.accounts, self.imports, self.operations = accounts, imports, operations

    def render(
        self,
        request: Request,
        account_id: int,
        status_code: int = 200,
        summary_id: int | None = None,
        **context: Any,
    ) -> HTMLResponse:
        """Render the page; `summary_id` is an import of the account to summarize.

        Raises:
            NotFoundError: no such account.
        """
        account = self.accounts.get(account_id)
        history = self.imports.list_for_account(account_id)
        context.setdefault("closed_on", date.today().isoformat())
        return render(
            request,
            "accounts/detail.html",
            status_code,
            account=account,
            freshness=self.accounts.get_freshness(account_id),
            imports=history,
            summary=next((item for item in history if item.id == summary_id), None),
            operations=self.operations.list_for_account(account_id),
            **context,
        )


AccountPageDep = Annotated[AccountPage, Depends()]
