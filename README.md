# autoquest

> Tools I build for me, and a showcase of how I design, build and ship software.

Life is full of quests!
**autoquest** is my answer: a monorepo of personal productivity apps, each one a little bot that completes a real-life quest for me.

## Quest log

| App | Quest | Status |
| --- | ----- | ------ |
| Banking | Keep track of my bank accounts and expenses | ⚪ Planned |

🟢 Live · 🟡 In progress · ⚪ Planned

## Repository layout

```
autoquest/
├── apps/        # one folder per app
├── libs/        # shared Python packages
├── infra/       # shared Terraform (bootstrap, modules, shared resources)
└── scripts/     # dev tooling
```

## Local setup

Prerequisites: [Docker](https://docs.docker.com/get-docker/) and [uv](https://docs.astral.sh/uv/).

```sh
uv sync                          # dev environment for every app
uv run pre-commit install        # format, lint and type checks on commit
docker compose up --build        # full local stack, bound to 127.0.0.1
uv run pytest                    # tests (integration tests need the stack's databases)
```

Each app's README explains its configuration and interfaces.

Development guidelines are in [CLAUDE.md](CLAUDE.md).

## License

[MIT](LICENSE)
