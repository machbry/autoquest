# Banking: technical architecture

> Components and the roadmap features each one supports. Feature scope lives in the
> [README roadmap](../README.md#roadmap) and the GitHub issues; general rules in the
> [root CLAUDE.md](../../../CLAUDE.md), banking overrides in [CLAUDE.md](../CLAUDE.md).

## Overview
A Postgres database is the single store for all banking data. A single FastAPI + HTMX web
app covers every user flow, from data editing to import, labelling and analysis. dbt turns the stored data into analysis models. Scheduled and
on-demand work runs as GitHub Actions jobs.

![Banking technical architecture](architecture.png)

Arrows: grey uses, blue reads and writes, green reads only. Dashed arrows and "(later)"
mark planned components. Source: [architecture.py](architecture.py).

## Components
| Component | Runs on | Features it supports |
| --- | --- | --- |
| **Web app** (FastAPI + HTMX) | Cloud Run | Accounts (declare, close); statement import with summary and freshness indicator; categories (add, rename, merge); labelling queue; manual operations and balances; corrections; monthly analysis pages |
| **Importers** (one module per bank/format, inside the web app) | Cloud Run | Banque Postale CSV; PDF statements; CFCAL and Fortuneo files; bank/account auto-detection |
| **Postgres** | Neon (`prd`), Docker (`loc`) | Stores all app data, for every feature |
| **dbt** (dbt-postgres) | Jobs, models in Postgres | Monthly analysis: spending by category, savings rate, net worth; internal transfer reporting |
| **Jobs** | GitHub Actions | Deploy; backups; analytics compute (`dbt build`); auto-labelling training and inference |
| **Cloud Storage** | GCP | Backups; trained auto-labelling model |
| **MCP server** (optional) | Cloud Run | Agent-assisted labelling; every journey also works without it |

## App data vs analytics
- **SQLAlchemy + Alembic own the `banking` schema**: the tables the app writes (accounts,
  imports, operations, categories, labels). Only Alembic migrations change them.
- **dbt owns the `analytics` schema**: it reads the `banking` tables as sources, never writes
  them, and builds the analysis models. Alembic never touches `analytics`.
- **The web app reads `analytics`** to show the analysis pages.
- **Contract**: dbt declares the `banking` tables as sources and holds tests on them.

## Data model
TODO: defined with #12 and #13.

## Security
TODO: defined with #14.
