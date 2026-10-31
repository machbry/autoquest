---
name: roadmap-update
description: Create, update or reprioritize an autoquest app's roadmap (Now/Next/Later in the app README). Use when building a roadmap from a feature list, adding an idea and deciding what moves, or reprioritizing after new information.
argument-hint: "<app> <update description>"
---

# Roadmap Update

> Adapted from [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins)
> (Apache-2.0, see `../LICENSE-knowledge-work-plugins`). Modified: trimmed for a solo developer,
> roadmap stored in the app README.

The user is a solo developer working on personal apps in their spare time. Capacity is small
and irregular, so the roadmap avoids dates.

## Where it lives

A `## Roadmap` section in `apps/<app>/README.md`, kept short:

```markdown
## Roadmap
**Objective:** one measurable outcome for the app (e.g. "know my monthly spending by
category in under 10 minutes a month").

| | Feature | Why | Issue |
|---|---|---|---|
| Now | ... | ... | #12 |
| Next | ... | ... | |
| Later | ... | ... | |
```

Issues (labels `<app>` + `feature`) hold the details and the status; the roadmap only orders
them. Don't duplicate specs in the README.

## Workflow

1. **Read the current state:** the app README and its open issues (GitHub MCP).
2. **Determine the operation:**
   - **Create:** agree on the app objective first, then list candidate features (from a
     brainstorm or the user) and prioritize them.
   - **Add:** place the new item and ask what moves down. Capacity is zero-sum.
   - **Reprioritize:** ask what changed. Show before/after.
   - **Done/cut:** remove the item (the closed issue is the history).
3. **Prioritize** with the simplest framework that works (see below).
4. **Propose the updated section**, then edit the README on approval. Suggest `/write-spec` for
   `Now` items that don't have an issue yet.

## Now / Next / Later
- **Now:** 1-2 items being built. Scoped, has an issue.
- **Next:** a few items, clear on what, not on when.
- **Later:** directional ideas; scope is flexible.

Every item must serve the app objective. If it doesn't, it's a non-goal.

## Prioritization
- **Value vs effort (default):** quick wins first, plan big bets carefully, drop low-value
  high-effort items.
- **ICE** when comparing more than ~5 items: Impact × Confidence × Ease, each 1-10.
- **MoSCoW** to scope a first usable version: Must / Should / Could / Won't.

Ship the smallest version that delivers the objective first (walking skeleton end to end),
then iterate.

## Dependencies
Flag sequential dependencies (B needs A's data or tables) and external ones (bank export
formats, free-tier limits). Prefer an order that removes them.

## Tips
- A roadmap orders outcomes, it is not a task list.
- Change it when new information arrives, not on a whim.
- If everything is Now, nothing is.
