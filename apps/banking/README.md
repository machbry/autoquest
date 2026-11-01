# banking

Keep track of my bank accounts and expenses: one labelled view of all my accounts, to see
where my money goes, my savings rate and my net worth over time.

Product discovery notes: [docs/discovery.md](docs/discovery.md).
Technical architecture: [docs/architecture.md](docs/architecture.md).

## Run locally
From the repo root, `docker compose up --build` starts Postgres, applies the migrations,
loads deterministic fake data (`banking-seed`, safe to re-run) and serves the app on
<http://127.0.0.1:8000>.

Tests need the stack, without the fake data: `docker compose up -d --build --wait
banking-web`, then `uv run pytest apps/banking --cov=banking`. Integration tests roll back
their writes; the e2e test deletes what it creates.

If a not-yet-merged migration was edited, reset the local database (fake data only):
`docker compose down -v`.

## Configuration
| Variable | Purpose |
| --- | --- |
| `BANKING_DB_URL` | Postgres URL, `postgresql+psycopg://…`; local default in [.env.example](.env.example) |
| `BANKING_E2E_URL` | Tests only: web app the e2e tests target (default `http://127.0.0.1:8000`) |

## Interfaces
| Interface | Description |
| --- | --- |
| `GET /accounts` | Accounts list (`GET /` redirects to it); create, edit, close or delete accounts from there |
| `GET /banks` | Banks list; create, rename, or delete a bank no account uses |
| `GET /healthz` | `{"status": "ok"}` when the app and its database answer |
| `banking` schema | Owned by Alembic (`src/banking/databases/migrations`); dbt reads it as a source |

Routes and code follow the [CRUD conventions](../../CLAUDE.md#crud-conventions).
New migration, generated from `databases/models` (review it before committing):
`uv run alembic -c apps/banking/alembic.ini revision --autogenerate -m "<Summary.>"`.

## Roadmap
**Objective:** every month, see where my money goes, my savings rate and my net worth across
all accounts since end 2024, for under 30 minutes of upkeep a month.

| | Feature | Why | Issue |
|---|---|---|---|
| Now | Accounts + Banque Postale current-account CSV import (dedup, freshness indicator) | High-volume account; 90-day CSV window loses data if missed | [#12](https://github.com/machbry/autoquest/issues/12) |
| Now | Labelling flow: categories, tags, "same as last time" suggestions, review queue | Labels are the core of every answer and the future training set | [#13](https://github.com/machbry/autoquest/issues/13) |
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
