"""The admin's views, one module per table.

They write the tables directly, not through the services: the database constraints
hold the invariants, and broken ones are shown to the user by name.
"""

from banking.admin.views.accounts import AccountView
from banking.admin.views.banks import BankView
from banking.admin.views.categories import CategoryView
from banking.admin.views.operations import OperationView

__all__ = ["AccountView", "BankView", "CategoryView", "OperationView"]
