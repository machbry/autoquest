---
name: write-spec
description: Write a feature spec for an autoquest app as a GitHub issue body, from a problem statement or feature idea. Use when turning a vague idea into a scoped feature with goals, non-goals, user stories, measurable success metrics and acceptance criteria, or when breaking a big ask into phases.
argument-hint: "<app> <feature or problem statement>"
---

# Write Spec

> Adapted from [anthropics/knowledge-work-plugins@a518709](https://github.com/anthropics/knowledge-work-plugins/tree/a518709449b0a32276af38c9b2a2f38c3219f5bc/product-management/skills/write-spec)
> (Apache-2.0, see `../LICENSE-knowledge-work-plugins`). Modified: trimmed for a solo developer,
> output is a GitHub issue following `CLAUDE.md`.

The user is a solo developer and the only user of their apps. No stakeholders, revenue or
competitors: value is time saved, errors avoided, or insight gained.

## Workflow

1. **Understand the feature.** Accept a feature name, a problem, or a vague idea. If the idea is
   too big for one PR-sized piece of work, propose phases and spec only the first one.
2. **Gather context**, conversationally, most important questions first (don't dump them all):
   - What problem does this solve, and how often does it happen?
   - What does the user do today instead, and what does it cost them (time, errors)?
   - How will we know it worked?
   - Constraints: data sources, formats, privacy.
   Read the app's `README.md` and existing open issues (GitHub MCP) to avoid duplicates and
   spot dependencies.
3. **Draft the issue body** with the structure below. Show it to the user before creating it.
4. **Iterate**, then on approval create the issue with labels `<app>` + `feature` (or `bug`).
   Suggested branch: `feat/<app>/<issue-number>-<short-description>`.

## Issue structure

```markdown
## Problem
2-3 sentences: the pain, how often, cost of not solving it.

## Goals
3-5 measurable outcomes (outcomes, not outputs).

## Non-goals
What this explicitly won't do, and why.

## User stories
- As <me in a specific situation>, I want <capability> so that <benefit>.

## Requirements
- **P0 (must):** ... each with acceptance criteria
- **P1 (nice):** ...
- **P2 (later, design for it):** ...

## Acceptance criteria
- Given ... When ... Then ...

## Success metrics
Metric, target, how and when it's measured.

## Security impact
Data touched, external inputs to validate, secrets, exposure (CLAUDE.md checklist).

## Cost
Services used and why it stays at €0 (free tier, quotas).

## Open questions
Tag each as blocking or non-blocking.
```

## Guidance

**Goals** are outcomes: "categorize a month of transactions in under 5 minutes", not "build a
categorization screen".

**Non-goals** prevent scope creep. Every spec has some. Good ideas that don't fit go to a
non-goal or to `Later` in the roadmap.

**User stories** are independent, valuable, small (one PR), and testable. Describe the need,
not the UI widget. Include error, empty and boundary cases.

**Priorities:** be ruthless with P0. Ask "if we cut this, does the feature still solve the
problem?" If yes, it isn't P0. P2s are architectural insurance, not a wish list.

**Acceptance criteria** cover the happy path, errors, edge cases and what must NOT happen.
Each one is independently testable and should map to an integration or e2e test (CLAUDE.md
requires at least one integration test per feature). Ban vague words ("fast", "intuitive"):
give numbers.

**Success metrics** for a personal app are usually:
- time to complete the task (before vs after);
- manual steps or corrections remaining;
- error rate (bad imports, miscategorized items);
- usage frequency (do I actually use it after a month?).
Give a target, a measurement method and an evaluation date: "≥ 90% of transactions
auto-categorized, measured by a SQL query, checked after 1 month".

**Tips**
- Prefer a tight spec to an expansive vague one.
- Only list genuinely open questions; answer what you can from the repo.
- Keep it scannable: headers and bold text should give the gist.
