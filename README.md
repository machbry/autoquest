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
Each app's README explains how to set it up and run it.

Development guidelines are in [CLAUDE.md](CLAUDE.md).

## License

[MIT](LICENSE)
