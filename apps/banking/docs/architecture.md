# Banking: technical architecture

> Components and the roadmap features each one supports. Feature scope lives in the
> [README roadmap](../README.md#roadmap) and the GitHub issues; general rules in the
> [root CLAUDE.md](../../../CLAUDE.md), banking overrides in [CLAUDE.md](../CLAUDE.md).

## Overview
A Postgres database is the single store for all banking data. A single FastAPI web app
covers every user flow: its own pages for import and analysis, and an admin built from
the database models for data editing and labelling. dbt turns the stored data into
analysis models. Scheduled and on-demand work runs as GitHub Actions jobs. The web app's code follows the three layers
(api → services → databases, around shared domains) of the
[root CLAUDE.md](../../../CLAUDE.md#app-code-structure).

![Banking technical architecture](architecture.png)

Arrows: grey uses, blue reads and writes, green reads only. Dashed arrows and "(later)"
mark planned components. Source: [architecture.py](architecture.py).

## Components
| Component | Runs on | Features it supports |
| --- | --- | --- |
| **Web app** (FastAPI pages) | Cloud Run | Import page: every account's data freshness, statement import with summary, monthly recap per account; manual operations and balances; corrections; monthly analysis pages |
| **Admin** (starlette-admin, inside the web app) | Cloud Run | Accounts (declare, edit, close, delete); banks (add, rename, delete); categories (add, rename, merge); operations table (search, filters, sort, labelling in place or in bulk) |
| **Importers** (one module per bank/format, inside the web app) | Cloud Run | Banque Postale CSV; PDF statements; CFCAL and Fortuneo files; bank/account auto-detection |
| **Postgres** | Neon (`prd`), Docker (`loc`) | Stores all app data, for every feature |
| **dbt** (dbt-postgres) | Jobs, models in Postgres | Monthly analysis: spending by category, savings rate, net worth; internal transfer reporting |
| **Jobs** | GitHub Actions | Deploy; backups; analytics compute (`dbt build`); auto-labelling training and inference |
| **Cloud Storage** | GCP | Backups; trained auto-labelling model |
| **MCP server** (optional) | Cloud Run | Agent-assisted labelling; every journey also works without it |

## App data vs analytics
- **SQLAlchemy + Alembic own the `banking` schema**: the tables the app writes (accounts,
  imports, operations, categories). Only Alembic migrations change them.
- **dbt owns the `analytics` schema**: it reads the `banking` tables as sources, never writes
  them, and builds the analysis models. Alembic never touches `analytics`.
- **The web app reads `analytics`** to show the analysis pages.
- **Contract**: dbt declares the `banking` tables as sources and holds tests on them.

## Data model
Defined in [databases/models](../src/banking/databases/models/).

- **`banks`**: the banks holding the accounts.
- **`accounts`**: the bank accounts, open or closed.
- **`imports`**: one row per imported export file.
- **`operations`**: the accounts' operations, labelled with a category or not.
- **`categories`**: the types of expense or income.

## Front end
- **App pages** (the Import page for now): server-rendered pages and plain forms, with
  no JavaScript: each action posts a form and redirects. Imports stay out of the admin:
  its CSRF check reads a whole upload before the app's size limit applies.
- **Admin** (`/admin`): [starlette-admin](https://jowilf.github.io/starlette-admin/),
  mounted in the app and built from the SQLAlchemy models, so a migrated column shows up
  there. Its JavaScript and CSS ship in the Python package, pinned by `uv.lock`; only the
  Inter font loads from a CDN. It writes the tables directly, not through the services:
  the database constraints hold the invariants, and it shows a broken one by its message.
  Its CSRF protection signs cookies with `BANKING_SECRET_KEY`.
- htmx, the stack's default, comes back (vendored and pinned) only where it clearly pays
  off.

## Security
TODO: defined with #14.
