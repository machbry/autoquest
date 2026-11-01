# CLAUDE.md

Development guidelines for **autoquest**, a monorepo of personal productivity apps that also
showcases my engineering practices. App descriptions live in `README.md` and in each app's README.

## Core principles
- **Keep it simple.** Build the smallest thing that works. No speculative abstractions, no
  premature generalization. Simplify whenever possible: deleting code is a feature.
- **Sobriety.** Keep CPU, memory, storage, network and dependency use low.
- **Zero cost.** Running the apps must cost €0: free tiers only. Before adopting any
  technology, check its current free-tier conditions (limits, regions, card required) against
  the expected usage. Scale to zero, cap quotas, and set budget alerts. Flag any design that
  could cost money.
- **Everything as code.** Infra, config, DB schema, seed data and CI/CD are code.
  A manual step is a last resort and is documented with the reason it can't be automated.
- **Secure by default.** Every feature goes through the security checklist below.
- **No AI in production.** LLMs and coding agents may help develop the code or label data for
  ML training. No production feature may depend on an LLM. An app may expose an optional
  agent interface (e.g. an MCP server) as long as every user journey works without it; using
  it sends data to the LLM provider, so the spec states what is exposed.
- **Concise docs.** Comments explain *why*, not *what*. Docs are short and updated in the same
  PR as the code.

## Tech stack
- **Languages:** Python 3.12+ and SQL. Another language only when Python isn't a reasonable fit;
  justify it in the PR.
- **Compute (APIs, MCP servers, UIs):** GCP Cloud Run.
- **Jobs:** GitHub Actions workflows (scheduled or on demand).
- **Relational database:** Neon (Postgres).
- **Analytics:** MotherDuck (DuckDB).
- **NoSQL database:** GCP Firestore.
- **File storage:** GCP Cloud Storage.
- **Container images:** GitHub Container Registry.
- **Secrets:** GCP Secret Manager (GitHub Actions secrets in CI).
- **UI:** NocoDB, self-hosted, on top of the app's database (schema stays in code).
- **Data pipelines:** dbt for data transformations.
- **IaC:** Terraform, with remote state in a GCS bucket.
- **Python tooling:** uv (workspace and lockfile), pytest, ruff (lint and format).
- **Local runtime:** Docker and Docker Compose.

## Repository structure
```
autoquest/
├── apps/<app>/               # one deployable app, self-contained
│   ├── src/<app>/            # Python package
│   ├── tests/{unit,integration,e2e}/
│   ├── infra/                # app Terraform (uses shared modules)
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── README.md             # purpose, setup, config, interfaces
├── libs/<lib>/               # shared Python packages
├── infra/
│   ├── bootstrap/            # one-time setup: project, state bucket, CI identity
│   ├── modules/              # reusable Terraform modules
│   └── shared/               # resources shared by apps (budgets, IAM)
├── scripts/                  # dev tooling (seeding, helpers)
├── .github/workflows/        # CI/CD
├── docker-compose.yml        # full local stack
├── pyproject.toml            # uv workspace root and tool config
└── CLAUDE.md
```

Rules:
- Apps never import each other. They communicate through explicit interfaces (HTTP API,
  tables, files, messages), and every interface has contract tests.
- Code moves to `libs/` only once a second app needs it.

## Naming conventions
- **Apps and libs:** short lowercase names (`banking`). Folders and cloud resources use
  kebab-case; Python packages use snake_case.
- **Environments:** `loc` (local) and `prd` (production).
- **Cloud resources:** `aq-<env>-<app>-<resource>`, e.g. `aq-prd-banking-api`. Globally unique
  names (buckets) get the project ID as a suffix.
- **Python:** PEP 8 (`snake_case` functions/modules, `PascalCase` classes, `UPPER_SNAKE`
  constants).
- **SQL:** `snake_case` identifiers, plural table names, `id` primary key, `<entity>_id`
  foreign keys, `created_at`/`updated_at` stored in UTC, keywords in UPPERCASE.
- **Environment variables:** `UPPER_SNAKE`, prefixed with the app name (`BANKING_DB_URL`).
- **Terraform:** `snake_case` resource names.

## Git workflow
- `main` is protected: changes go through a PR, no force push.
- One PR per concern, ideally scoped to one app.
- Use the GitHub MCP server for GitHub operations (issues, PRs, labels, reviews), not the
  `gh` CLI.
- **Branches:** `<type>/<scope>/<short-description>`, lowercase kebab-case, e.g.
  `feat/banking/import-ofx`, `fix/infra/state-bucket-iam`. Add the issue number if there
  is one: `feat/banking/12-import-ofx`.
- **Commits** ([Conventional Commits](https://www.conventionalcommits.org)):
  `<type>(<scope>): <summary>`, e.g. `feat(banking): import OFX statements`.
  - Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `chore`.
  - Scope: an app or lib name, or `infra`, `ci`, `repo` for cross-cutting changes.
  - Summary: imperative, at most 72 characters, no final period. Mark breaking changes with `!`.
  - Every commit on a branch follows this format, since it lands in `main` history as is.
    The PR title uses it too.

## Issues
Every issue gets exactly one scope label and one type label, so issues can be filtered by either:
- **Scope:** the app name (`banking`), or `core` for repo-wide work (tooling, CI/CD, infra,
  governance). Add a label when a new app is created.
- **Type:** `feature` (new feature or improvement) or `bug`.

The issue's labels map to the branch and commit: `bug` → `fix`, `feature` → `feat` (or
another type when more precise); the scope label is the commit scope (`core` becomes `infra`,
`ci` or `repo`).

## Testing
pytest. Tests live in `apps/<app>/tests/{unit,integration,e2e}`.

- **Unit tests** where they add value:
  - logic with McCabe complexity ≥ 5 (ruff `C901` hard limit: 10);
  - non-trivial business rules;
  - interfaces between apps and libs (contract tests).

  Test behavior through public interfaces. Never write tests that mirror the implementation
  (private helpers, asserted call sequences, mocks of internals) just to raise coverage.
- **Integration tests:** at least one per feature, against real local dependencies
  (Docker Compose services).
- **End-to-end tests:** at least one per app, covering its main user journey on the running
  stack.
- **Regression tests:** every bug fix starts with a test that reproduces the bug.
- **Coverage:** at least 80% per app, enforced in CI. It's a floor, not a goal: if coverage is
  low, add meaningful tests or delete dead code.
- **Test data:** fake data only (factories, Faker). Never real personal data.

## Code style
- **Formatter:** `ruff format` (Black-compatible, line length 88).
- **Linter:** ruff, with the `E`, `F`, `I`, `B`, `UP`, `S`, `C90` and `D` rule sets.
- **Docstrings:** Google style for public modules, classes and functions. A one-liner is enough
  when it says everything.
- **Type hints** on all public functions.
- **Config** comes from environment variables, validated at startup. No hard-coded
  environment-specific values.

## Security checklist (every feature)
- No secrets in code or git. Locally: `.env` (gitignored) plus a committed `.env.example`.
  In production: Secret Manager.
- Validate all external input. Use parameterized SQL only.
- Least privilege: one service account per app, with only the roles it needs.
- Endpoints are private by default and authenticated when exposed.
- CI authenticates to GCP through Workload Identity Federation, never service account keys;
  to other providers (Neon, MotherDuck) with scoped API tokens stored in GitHub Actions
  secrets.
- Dependencies are pinned (`uv.lock`) and scanned for vulnerabilities.
- Personal data: collect as little as possible, never commit it, never log it.
- Each PR description states the feature's security impact.

## Environments and CI/CD
- `loc`: the full stack in Docker Compose. `prd`: the cloud services above.
- **On PR:** format check, lint, tests with coverage, `terraform fmt`/`validate`/`plan`,
  dependency and secret scans.
- **On merge to `main`:** build images, `terraform apply`, deploy to `prd`.
- **Manual steps** (the only ones):
  - running `infra/bootstrap` once (project, state bucket, CI identity);
  - GitHub repository settings (ruleset on `main`, labels), set in the GitHub UI: managing
    them as code needs a long-lived GitHub token, not worth the risk for a solo repo.

## Local development
- Prerequisites: Docker, uv (and Terraform for infra work).
- `docker compose up` starts every app and its dependencies. Databases are initialized with a
  schema and deterministic fake data automatically.
- Common commands (from the repo root):
  - `uv sync`: install dependencies
  - `uv run ruff format . && uv run ruff check .`: format and lint
  - `uv run pytest`: run tests
  - `docker compose up --build`: run the local stack

## Documentation
- `README.md` lists the apps and explains how to set them up and run them (at least locally).
- Each app's README covers its purpose, setup, configuration and interfaces.
- `CLAUDE.md` holds development guidelines only.

## Definition of done
- [ ] Required tests written (unit where relevant, integration, e2e for new apps, regression
      for bugs)
- [ ] Coverage ≥ 80%, CI green
- [ ] Security checklist reviewed
- [ ] Runs at €0 (free tier)
- [ ] Everything as code, no undocumented manual step
- [ ] Docs updated (README, app README) and kept concise
