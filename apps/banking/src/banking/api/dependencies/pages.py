"""Pages that several routers render, with the services they show."""

from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse

from banking.api.dependencies.services import (
    AccountServiceDep,
    ImportServiceDep,
    OperationServiceDep,
)
from banking.api.rendering import render


class ImportPage:
    """The Import page: every account's freshness, and the chosen account's imports.

    The page route and the upload route both render it, the latter with its errors.
    """

    def __init__(
        self,
        accounts: AccountServiceDep,
        imports: ImportServiceDep,
        operations: OperationServiceDep,
    ) -> None:
        """Use the request's services."""
        self.accounts, self.imports = accounts, imports
        self.operations = operations

    def render(
        self,
        request: Request,
        account_id: int | None = None,
        status_code: int = 200,
        summary_id: int | None = None,
        **context: Any,
    ) -> HTMLResponse:
        """Render the page; with `account_id`, that account's upload form and history.

        `summary_id` is an import of the account to summarize.

        Raises:
            NotFoundError: no such account.
        """
        if account_id is not None:
            history = self.imports.list_for_account(account_id)
            context |= {
                "account": self.accounts.get(account_id),
                "freshness": self.accounts.get_freshness(account_id),
                "imports": history,
                "summary": next((i for i in history if i.id == summary_id), None),
                "recap": self.operations.recap(account_id),
            }
        return render(
            request,
            "imports/list.html",
            status_code,
            accounts=self.accounts.list_with_freshness(),
            **context,
        )


ImportPageDep = Annotated[ImportPage, Depends()]
