# CLAUDE.md: banking

Banking-specific rules. They add to the [root CLAUDE.md](../../CLAUDE.md) and override it
where stated.

@docs/architecture.md

## Rules
- **Money:** `Decimal` in Python, `NUMERIC` in Postgres, never `float`.
- **Business dates** (operation, export, opened/closed) are `DATE` with no timezone. The root
  "stored in UTC" rule applies to `created_at`/`updated_at` only.
- **Invariants live in the database** (constraints, foreign keys): several components write
  to the tables (web app, later the MCP server and the auto-labelling job).
- **Logging, stricter than root:** log ids, counts and line numbers only. Never descriptions,
  amounts, account numbers, tags or notes.
- **Persistence:** SQLAlchemy models and Alembic migrations own the `banking` schema; dbt owns
  `analytics` and only reads `banking`. Never mix the two.

## Overrides of the default stack
- **No MotherDuck:** analytics run with dbt-postgres on the Neon database; the volume
  (~1,100 operations a year) doesn't justify a second store. Revisit if it grows.
- **No NocoDB:** one FastAPI + HTMX app covers every flow, data editing included: one
  service and one auth surface, and every write goes through the app's validation.
- **No Firestore.**
- **Raw statement files are never stored:** only parsed operations and import metadata.
