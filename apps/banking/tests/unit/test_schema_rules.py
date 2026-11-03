"""The models follow the SQL, money and date rules of the CLAUDE.md files.

Read from the models and their compiled DDL: no database needed.
"""

import re

import pytest
from sqlalchemy import Date, DateTime, Float, Numeric, Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from banking.databases.models import Base

TABLES = Base.metadata.sorted_tables


def by_name(table: Table) -> str:
    return table.name


def ddl_names(table: Table) -> list[str]:
    """Constraint and index names as the database gets them."""
    dialect = postgresql.dialect()
    ddl = str(CreateTable(table).compile(dialect=dialect))
    ddl += "".join(
        str(CreateIndex(index).compile(dialect=dialect)) for index in table.indexes
    )
    return re.findall(r"(?:CONSTRAINT|INDEX) (\w+)", ddl)


@pytest.mark.parametrize("table", TABLES, ids=by_name)
def test_constraints_are_named_after_their_table(table):
    # Services map a violation back to the field at fault by the constraint's name.
    pattern = re.compile(rf"(pk|uq|ck|fk|ix)_{table.name}(_\w+)?")

    assert [name for name in ddl_names(table) if not pattern.fullmatch(name)] == []


@pytest.mark.parametrize("table", TABLES, ids=by_name)
def test_table_and_keys_follow_sql_naming(table):
    assert re.fullmatch(r"[a-z]+(_[a-z]+)*s", table.name), "snake_case and plural"
    assert [column.name for column in table.primary_key] == ["id"]
    assert [
        key.parent.name
        for key in table.foreign_keys
        if not key.parent.name.endswith("_id")
    ] == []


@pytest.mark.parametrize("table", TABLES, ids=by_name)
def test_money_is_never_a_float(table):
    assert [c.name for c in table.columns if isinstance(c.type, Float)] == []
    assert [
        c.name
        for c in table.columns
        if isinstance(c.type, Numeric) and not c.type.asdecimal
    ] == []


@pytest.mark.parametrize("table", TABLES, ids=by_name)
def test_timestamps_are_utc_and_business_dates_are_dates(table):
    timestamps = [c for c in table.columns if c.name in {"created_at", "updated_at"}]
    business_dates = [c for c in table.columns if c.name.endswith(("_date", "_on"))]

    assert all(isinstance(c.type, DateTime) and c.type.timezone for c in timestamps), (
        "created_at/updated_at are stored with their time zone (UTC)"
    )
    assert all(isinstance(c.type, Date) for c in business_dates), "DATE, no time zone"
