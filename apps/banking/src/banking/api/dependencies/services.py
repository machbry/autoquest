"""Services injected into the routers, bound to the request's session."""

from typing import Annotated

from fastapi import Depends

from banking.api.dependencies.database import SessionDep
from banking.services.accounts.account_service import AccountService
from banking.services.banks.bank_service import BankService
from banking.services.imports.import_service import ImportService
from banking.services.operations.operation_service import OperationService


def get_account_service(session: SessionDep) -> AccountService:
    """Account use cases for this request."""
    return AccountService(session)


def get_bank_service(session: SessionDep) -> BankService:
    """Bank use cases for this request."""
    return BankService(session)


def get_import_service(session: SessionDep) -> ImportService:
    """Import use cases for this request."""
    return ImportService(session)


def get_operation_service(session: SessionDep) -> OperationService:
    """Operation use cases for this request."""
    return OperationService(session)


AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]
BankServiceDep = Annotated[BankService, Depends(get_bank_service)]
ImportServiceDep = Annotated[ImportService, Depends(get_import_service)]
OperationServiceDep = Annotated[OperationService, Depends(get_operation_service)]
