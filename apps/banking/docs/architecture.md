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
