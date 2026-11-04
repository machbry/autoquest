"""Data editing: label operations, edit accounts, categories and banks.

A starlette-admin interface built from the SQLAlchemy models, so a column a migration
adds shows up here. Only `main.py` mounts it; no layer imports it.
"""

import logging

from sqlalchemy.orm import Session, sessionmaker
from starlette_admin import Link
from starlette_admin.contrib.sqla import Admin

from banking.admin.views import AccountView, BankView, CategoryView, OperationView
from banking.databases.models import (
    AccountModel,
    BankModel,
    CategoryModel,
    OperationModel,
)

# Its logs quote searches, filters and the database's messages, which hold the values
# at fault (names, descriptions): off at every level, the app logs what it needs itself.
logging.getLogger("starlette_admin").setLevel(logging.CRITICAL + 1)


def create_admin(sessions: sessionmaker[Session], secret_key: str) -> Admin:
    """The admin, each request in its own session (committed if it succeeds).

    `secret_key` signs its CSRF and flash cookies.
    """
    admin = Admin(sessions, title="Banking", base_url="/admin", secret_key=secret_key)
    admin.add_view(Link("Import", url="/imports"))
    admin.add_view(OperationView(OperationModel))
    admin.add_view(AccountView(AccountModel))
    admin.add_view(CategoryView(CategoryModel))
    admin.add_view(BankView(BankModel))
    return admin
