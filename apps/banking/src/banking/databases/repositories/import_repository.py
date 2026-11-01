"""Data access to imports."""

from collections.abc import Mapping, Sequence
from datetime import date

from sqlalchemy import func, select

from banking.databases.models import ImportModel
from banking.databases.repositories.base import Repository
from banking.domains.import_ import Import


class ImportRepository(Repository[ImportModel, Import]):
    """Imports of export files."""

    model = ImportModel

    def to_domain(self, row: ImportModel) -> Import:
        """Convert a row to its domain object."""
        return Import(
            id=row.id,
            account_id=row.account_id,
            export_date=row.export_date,
            balance=row.balance,
            first_operation_on=row.first_operation_on,
            last_operation_on=row.last_operation_on,
            rows_in_file=row.rows_in_file,
            rows_new=row.rows_new,
            created_at=row.created_at,
        )

    def list_for_account(self, account_id: int) -> Sequence[Import]:
        """An account's imports, latest export first."""
        rows = self.session.scalars(
            select(ImportModel)
            .filter_by(account_id=account_id)
            .order_by(ImportModel.export_date.desc(), ImportModel.id.desc())
        )
        return [self.to_domain(row) for row in rows]

    def latest_export_dates(self) -> Mapping[int, date]:
        """Account id → export date of its latest export, for accounts with imports."""
        rows = self.session.execute(
            select(ImportModel.account_id, func.max(ImportModel.export_date)).group_by(
                ImportModel.account_id
            )
        )
        return {account_id: export_date for account_id, export_date in rows}
