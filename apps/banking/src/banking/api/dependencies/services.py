"""Services injected into the routers, bound to the request's session."""

from typing import Annotated

from fastapi import Depends

from banking.api.dependencies.database import SessionDep
from banking.services.accounts.account_service import AccountService
from banking.services.banks.bank_service import BankService


def get_account_service(session: SessionDep) -> AccountService:
    """Account use cases for this request."""
    return AccountService(session)


def get_bank_service(session: SessionDep) -> BankService:
    """Bank use cases for this request."""
    return BankService(session)


AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]
BankServiceDep = Annotated[BankService, Depends(get_bank_service)]
