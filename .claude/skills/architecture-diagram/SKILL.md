---
name: architecture-diagram
description: Create or update an autoquest app's technical architecture diagram (`apps/<app>/docs/architecture.py`, rendered to PNG with the diagrams library). Use when adding, removing or rewiring a component (service, store, job), when a new app needs its architecture documented, or when the architecture diagram looks wrong.
argument-hint: "<app> [change]"
---

# Architecture Diagram

Architecture diagrams are code: never hand-write Mermaid or ASCII architecture diagrams.

## Files
| File | Role |
| --- | --- |
| `apps/<app>/docs/architecture.py` | Diagram source, one per app (required) |
| `apps/<app>/docs/architecture.png` | Rendered image, committed |
| `apps/<app>/docs/architecture.md` | Embeds the PNG, legend, components table |
| `scripts/architecture/autoquest_diagrams.py` | Shared helpers: `app_diagram`, `uses`, `reads_writes`, `reads`, `later` |
| `scripts/architecture/render.py` | Renderer, run in Docker (Graphviz is in the image) |

Render from the repo root (Docker must be running):
```
docker compose run --rm --build architecture <app>   # or no app: all apps
```
Don't run `architecture.py` directly or install Graphviz locally.

## Conventions
- Start from `with app_diagram("<App name>"):`. Don't pass layout attributes in app files:
  change `app_diagram` instead, so every app stays consistent.
- One `Cluster` per runtime (`Cloud Run`, `Postgres: Neon`, `GitHub Actions jobs`...).
- Edges only through the helpers: `uses()` (grey: a client calling a service),
  `reads_writes()` (blue), `reads()` (green). Write `src >> reads() >> store`.
- Planned components: `later("Label")` on the node and `planned=True` on each of its edges
  (dashed).
- Node classes for the stack:

  | Component | Class |
  | --- | --- |
  | User | `diagrams.onprem.client.User` |
  | FastAPI web app | `diagrams.programming.framework.Fastapi` |
  | Other Cloud Run service | `diagrams.gcp.compute.Run` |
  | Postgres (Neon), one node per schema | `diagrams.onprem.database.Postgresql` |
  | GitHub Actions job | `diagrams.onprem.ci.GithubActions` |
  | dbt job | `diagrams.onprem.analytics.Dbt` |
  | Cloud Storage | `diagrams.gcp.storage.GCS` |
  | Firestore | `diagrams.gcp.database.Firestore` |
  | MotherDuck / DuckDB | `diagrams.onprem.database.Duckdb` |

  Anything else: search the [diagrams nodes docs](https://diagrams.mingrammer.com/docs/nodes/onprem)
  and prefer a generic node over a misleading icon.
- Stay high-level, like the rest of the architecture doc: components and who accesses what.
  No tables, endpoints or flows.

## Workflow
1. Read the app's `docs/architecture.md`, `CLAUDE.md` and existing `docs/architecture.py`.
2. Edit `architecture.py` (new app: copy `apps/banking/docs/architecture.py` as a template).
3. Render, then **Read the PNG** to check it: every component and edge present, colours and
   dashes right, no edge crossing a label. Graphviz places nodes from the edges, so fix
   layout by changing edge declaration order or clusters, not node order.
4. Update `architecture.md`: the components table, and the image plus legend below if the
   doc doesn't have them yet.
5. Commit `architecture.py` and `architecture.png` together.

## Legend snippet for `architecture.md`
```markdown
![<App> technical architecture](architecture.png)

Arrows: grey uses, blue reads and writes, green reads only. Dashed arrows and "(later)"
mark planned components. Source: [architecture.py](architecture.py).
```
