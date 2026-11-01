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
| `scripts/architecture/autoquest_diagrams.py` | Shared helpers: `app_diagram`, `provider`, `component`, `uses`, `reads_writes`, `reads` |
| `scripts/architecture/icons/` | Provider logos the diagrams package lacks (PNG) |
| `scripts/architecture/render.py` | Renderer, run in Docker (Graphviz is in the image) |

Render from the repo root (Docker must be running):
```
docker compose run --rm --build architecture <app>   # or no app: all apps
```
Don't run `architecture.py` directly or install Graphviz locally.

## Conventions
- Start from `with app_diagram("<App name>"):`. Don't pass layout attributes in app files:
  change `app_diagram` instead, so every app stays consistent.
- **Clusters:** one per provider, `with provider("<Provider>"):`; its title shows the
  provider's logo. Known providers are in `PROVIDER_ICONS`: `Google Cloud`, `GitHub`,
  `Neon`. For a new one, map it to the diagrams package's logo if there is one, else add a
  PNG to `scripts/architecture/icons/` (Graphviz here loads PNG, not SVG). The user stays
  outside any cluster.
- **Components:** always `component(Icon, name, feature, technology)`, never a bare node
  class. The node shows the icon, then three lines:
  1. **name**: the resource name from the root `CLAUDE.md` cloud naming convention, with
     `prd`: `aq-prd-banking-web`, bucket `aq-prd-banking-data-<project-id>`. GitHub Actions
     workflows follow the same pattern (`aq-prd-banking-backup`). Database schemas keep
     their SQL name (`banking`).
  2. **feature**: what it does for the app, in a few words (`Backups`).
  3. **technology**: the service or technology it runs on (`Cloud Run Service`,
     `GitHub Actions`, `PostgreSQL schema`, `dbt on GitHub Actions`).
- **Icons** show what the component is built on: the managed service for services and
  jobs, the tool when one defines the job (dbt, Terraform). Never a programming-language
  icon: too generic.

  | Component | Icon class |
  | --- | --- |
  | User | `diagrams.onprem.client.User` |
  | Cloud Run service | `diagrams.gcp.compute.Run` |
  | Cloud Storage bucket | `diagrams.gcp.storage.GCS` |
  | Firestore | `diagrams.gcp.database.Firestore` |
  | GitHub Actions workflow | `diagrams.onprem.ci.GithubActions` |
  | dbt job | `diagrams.onprem.analytics.Dbt` |
  | Terraform job | `diagrams.onprem.iac.Terraform` |
  | PostgreSQL schema (Neon) | `diagrams.onprem.database.Postgresql` |
  | MotherDuck database | `diagrams.onprem.database.Duckdb` |

  Anything else: search the [diagrams nodes docs](https://diagrams.mingrammer.com/docs/nodes/onprem).
- **Edges** only through the helpers: `uses()` (grey: a client calling a service),
  `reads_writes()` (blue), `reads()` (green). Write `src >> reads() >> store`.
- **Planned** components: `planned=True` on `component` (adds "(later)" to the feature)
  and on each of its edges (dashed).
- Stay high-level, like the rest of the architecture doc: components and who accesses what.
  No tables, endpoints or flows.

## Workflow
1. Read the app's `docs/architecture.md`, `CLAUDE.md` and existing `docs/architecture.py`.
2. Edit `architecture.py` (new app: copy `apps/banking/docs/architecture.py` as a template).
3. Render, then **Read the PNG** to check it: every component and edge present, colours and
   dashes right. Graphviz places nodes from the edges and ignores declaration order, so
   don't spend long on layout: fix it in `app_diagram` for every app, or accept a minor
   crossing.
4. Update `architecture.md`: the components table, and the image plus legend below if the
   doc doesn't have them yet.
5. Commit `architecture.py` and `architecture.png` together.

## Legend snippet for `architecture.md`
```markdown
![<App> technical architecture](architecture.png)

Arrows: grey uses, blue reads and writes, green reads only. Dashed arrows and "(later)"
mark planned components. Source: [architecture.py](architecture.py).
```
