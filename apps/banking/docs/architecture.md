# Banking: technical architecture

> Components and the roadmap features each one supports. Feature scope lives in the
> [README roadmap](../README.md#roadmap) and the GitHub issues; general rules in the
> [root CLAUDE.md](../../../CLAUDE.md), banking overrides in [CLAUDE.md](../CLAUDE.md).

## Overview
A Postgres database is the single store for all banking data. A single FastAPI + HTMX web
app covers every user flow, from data editing to import, labelling and analysis. dbt turns the stored data into analysis models. Scheduled and
on-demand work runs as GitHub Actions jobs.

```mermaid
flowchart LR
    user([Me, desktop browser])
    subgraph run[Cloud Run]
        web[Web app<br/>FastAPI + HTMX<br/>+ importers]
        mcp[MCP server]
    end
    subgraph pg[Postgres: Neon]
        banking[(banking schema)]
        analytics[(analytics schema)]
    end
    subgraph gha[GitHub Actions jobs]
        deploy[Deploy]
        backup[Backup]
        dbt[Analytics]
        ml[Auto-labelling]
    end
    gcs[(Cloud Storage)]

    user --> web
    web --> banking
    web --> analytics
    mcp -.-> banking
    dbt --> banking
    dbt --> analytics
    backup --> banking
    backup --> gcs
    ml -.-> banking
    ml -.-> gcs

    subgraph legend[Legend]
        direction LR
        k1[ ] -- uses --> k2[ ]
        k3[ ] -- reads and writes --> k4[ ]
        k5[ ] -- reads only --> k6[ ]
        k7[Later]
    end

    classDef key fill:none,stroke:none
    class k1,k2,k3,k4,k5,k6 key
    classDef later stroke-dasharray:5 5
    class mcp,ml,k7 later
    linkStyle 0,10 stroke:#6b7280,stroke-width:2px
    linkStyle 1,3,5,7,8,9,11 stroke:#2563eb,stroke-width:2px
    linkStyle 2,4,6,12 stroke:#16a34a,stroke-width:2px
```

## Components
| Component | Runs on | Roadmap features it supports |
| --- | --- | --- |
| **Web app** (FastAPI + HTMX) | Cloud Run | Declare/close accounts, CSV import with summary and freshness indicator ([#12](https://github.com/machbry/autoquest/issues/12)); categories (add, rename, merge) and labelling queue ([#13](https://github.com/machbry/autoquest/issues/13)); manual operations and balances, corrections, monthly analysis pages (Next); PDF and other banks' imports (Next/Later) |
| **Importers** (one module per bank/format, inside the web app) | Cloud Run | Banque Postale CSV (#12); PDF backfill (Next); CFCAL/Fortuneo files and bank/account auto-detection (Later) |
| **Postgres** | Neon (`prd`), Docker (`loc`) | Stores all app data, for every feature |
| **dbt** (dbt-postgres) | Jobs, models in Postgres | Monthly analysis: spending by category, savings rate, net worth; internal transfer reporting (Next) |
| **Jobs** | GitHub Actions | Deploy and backups ([#14](https://github.com/machbry/autoquest/issues/14)); analytics compute with `dbt build` (Next); auto-labelling training and inference (Later) |
| **Cloud Storage** | GCP | Backups (#14); trained auto-labelling model (Later) |
| **MCP server** (optional) | Cloud Run | Agent-assisted labelling (Later); every journey also works without it |

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
