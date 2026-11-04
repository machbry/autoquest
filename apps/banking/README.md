# banking

Keep track of my bank accounts and expenses: one labelled view of all my accounts, to see
where my money goes, my savings rate and my net worth over time.

Product discovery notes: [docs/discovery.md](docs/discovery.md).
Technical architecture: [docs/architecture.md](docs/architecture.md).

## Run locally
From the repo root, `docker compose up --build` starts Postgres, applies the migrations,
loads deterministic fake data (`banking-seed`: banks, accounts, two overlapping fake
exports, categories, and labels for the first export, so the operations table has
labelled and unlabelled rows; safe to re-run) and serves the app on
<http://127.0.0.1:8000>.

Tests need the stack, without the fake data: `docker compose up -d --build --wait
banking-web`, then `uv run pytest apps/banking --cov=banking`. Integration tests roll back
their writes; the e2e test deletes what it creates.

If a not-yet-merged migration or the fake data changed, reset the local database (fake data
only): `docker compose down -v`.

## Configuration
| Variable | Purpose |
| --- | --- |
| `BANKING_DB_URL` | Postgres URL, `postgresql+psycopg://…`; local default in [.env.example](.env.example) |
| `BANKING_SECRET_KEY` | Signs the admin's CSRF and flash cookies, 32 characters at least; the same on every instance |
| `BANKING_E2E_URL` | Tests only: web app the e2e tests target (default `http://127.0.0.1:8000`) |

## Interfaces
| Interface | Description |
| --- | --- |
| `GET /imports` | Import page (`GET /` redirects to it): every account with its data freshness. `?account_id=` shows that account's upload form, monthly recap (operations, labelled, unlabelled, each month linking to its operations in the admin) and imported files |
| `POST /accounts/{id}/imports` | Import operations from a La Banque Postale CSV file (multipart `file`, 1 MB max) from the Import page, which then shows its summary |
| `GET /admin/operations/list` | Operations table ([starlette-admin](https://jowilf.github.io/starlette-admin/)): search, filters (`filter` in the address, e.g. `account__in=1 AND category__is_null`), sort; request logs keep only the method, path and status, never the query. Set a category in its cell, or on the selected rows (or every row the filters keep) with *Set category* and *Remove category*; the bank's fields are read-only |
| `GET /admin/accounts/list` | Accounts: declare, edit, *Close* (keeps the history; no reopening), or delete with all their history |
| `GET /admin/categories/list` | Categories: create, rename, *Merge into…* another, or delete one no operation uses |
| `GET /admin/banks/list` | Banks: create, rename, or delete one no account uses |
| `GET /healthz` | `{"status": "ok"}` when the app and its database answer |
| `banking` schema | Owned by Alembic (`src/banking/databases/migrations`); dbt reads it as a source |

Routes and code follow the [CRUD conventions](../../CLAUDE.md#crud-conventions), except
the admin (`src/banking/admin`): built from the SQLAlchemy models, it writes the tables
directly, and the database constraints hold the invariants.
New migration, generated from `databases/models` (review it before committing):
`uv run alembic -c apps/banking/alembic.ini revision --autogenerate -m "<Summary.>"`.

## Roadmap
**Objective:** every month, see where my money goes, my savings rate and my net worth across
all accounts since end 2024, for under 30 minutes of upkeep a month.

| | Feature | Why | Issue |
|---|---|---|---|
| Now | Clean, consistent look | ~30 min a month in the app; pages easier to scan | [#35](https://github.com/machbry/autoquest/issues/35) |
| Next | Deploy: private, in the cloud, durable data | Required before the other Next items; data survives a laptop loss | [#14](https://github.com/machbry/autoquest/issues/14) |
| Next | Monthly analysis: spending by category, savings rate, net worth | Turns labels into the objective's answers | |
| Next | Internal transfer detection | Without it, transfers inflate spending and distort savings rate | |
| Next | Manual operations and balances (Goodvest, cash, corrections) | Completes net worth; balances check import completeness | |
| Next | PDF statement backfill (Banque Postale, back to end 2024) | History beyond the 90-day CSV window | |
| Later | Shared-sheet matching for "my share" | Automates what can be entered by hand while labelling | |
| Later | Other banks' files (CFCAL CSV, Fortuneo PDF), auto-detect bank/account | Low volume, manual entry works meanwhile | |
| Later | Email context; auto-labelling trained on validated labels | Needs a labelled history first | |
| Later | MCP interface for agent-assisted labelling (optional, private, authenticated) | Faster labelling from an agent; the web flow stays complete without it | |

Dependencies: analysis needs labels; savings rate needs transfer detection; net worth needs
balances. PDF backfill depends on riskiest assumption 3 (statements add up): test it before
speccing.
