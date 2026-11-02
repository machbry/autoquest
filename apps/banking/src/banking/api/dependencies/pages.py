"""Pages that several routers render, with the services they show."""

from collections.abc import Collection
from datetime import date
from typing import Annotated, Any, Protocol

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse

from banking.api.dependencies.services import (
    AccountServiceDep,
    BankServiceDep,
    CategoryServiceDep,
    ImportServiceDep,
    LabelServiceDep,
    OperationServiceDep,
)
from banking.api.rendering import render
from banking.domains.operation import MAX_SELECTION, OperationFilter, OperationSort


class AccountPage:
    """An account's page: details, freshness, imports, operations and their labels.

    The account routes and the import route both render it, with their own errors.
    """

    def __init__(
        self,
        accounts: AccountServiceDep,
        imports: ImportServiceDep,
        operations: OperationServiceDep,
        labels: LabelServiceDep,
    ) -> None:
        """Use the request's services."""
        self.accounts, self.imports = accounts, imports
        self.operations, self.labels = operations, labels

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
            labels=self.labels.list_for_account(account_id),
            **context,
        )


class TableQuery(Protocol):
    """What the operations table needs from its query (the routers' schema)."""

    @property
    def id(self) -> list[int]: ...  # noqa: D102

    @property
    def select(self) -> str | None: ...  # noqa: D102

    @property
    def similar_to(self) -> int | None: ...  # noqa: D102

    def to_filter(self) -> OperationFilter: ...  # noqa: D102

    def to_sort(self) -> OperationSort: ...  # noqa: D102


class OperationsPage:
    """The operations table: filters, rows, ticked rows and the bulk actions.

    The table route and the label actions (on errors) both render it.
    """

    def __init__(
        self,
        operations: OperationServiceDep,
        banks: BankServiceDep,
        accounts: AccountServiceDep,
        categories: CategoryServiceDep,
    ) -> None:
        """Use the request's services."""
        self.operations, self.banks = operations, banks
        self.accounts, self.categories = accounts, categories

    def render(
        self,
        request: Request,
        query: TableQuery,
        status_code: int = 200,
        **context: Any,
    ) -> HTMLResponse:
        """Render the table for this query; `context` adds to (or overrides) it."""
        rows = self.operations.list(query.to_filter(), query.to_sort())
        ticked = set(query.id)
        if query.select == "all":
            added: Collection[int] = [row.operation.id for row in rows]
        elif query.similar_to is not None:
            added = self.operations.similar_ids(rows, query.similar_to)
        else:
            added = ()
        if len(ticked.union(added)) > MAX_SELECTION:
            context.setdefault("errors", {})["select"] = (
                f"At most {MAX_SELECTION} operations at once: narrow the filters."
            )
        else:
            ticked.update(added)
        # Ticked rows first, each part in the chosen order: the selection stays in
        # view, next to the actions.
        rows = sorted(rows, key=lambda row: row.operation.id not in ticked)
        return render(
            request,
            "operations/list.html",
            status_code,
            query=query,
            rows=rows,
            ticked=ticked,
            banks=self.banks.list(),
            accounts=self.accounts.list(),
            categories=self.categories.list(),
            **context,
        )


AccountPageDep = Annotated[AccountPage, Depends()]
OperationsPageDep = Annotated[OperationsPage, Depends()]
