# banking

Keep track of my bank accounts and expenses: one labelled view of all my accounts, to see
where my money goes, my savings rate and my net worth over time.

Product discovery notes: [docs/discovery.md](docs/discovery.md).

## Roadmap
**Objective:** every month, see where my money goes, my savings rate and my net worth across
all accounts since end 2024, for under 30 minutes of upkeep a month.

| | Feature | Why | Issue |
|---|---|---|---|
| Now | Accounts + Banque Postale current-account CSV import (dedup, freshness indicator) | High-volume account; 90-day CSV window loses data if missed | [#12](https://github.com/machbry/autoquest/issues/12) |
| Now | Labelling flow: categories, tags, "same as last time" suggestions, review queue | Labels are the core of every answer and the future training set | [#13](https://github.com/machbry/autoquest/issues/13) |
| Now | Deploy to prd: private Cloud Run, durable SQLite | Required before Next; data survives a laptop loss | [#14](https://github.com/machbry/autoquest/issues/14) |
| Next | Monthly analysis: spending by category, savings rate, net worth | Turns labels into the objective's answers | |
| Next | Internal transfer detection | Without it, transfers inflate spending and distort savings rate | |
| Next | Manual operations and balances (Goodvest, cash, corrections) | Completes net worth; balances check import completeness | |
| Next | PDF statement backfill (Banque Postale, back to end 2024) | History beyond the 90-day CSV window | |
| Later | Shared-sheet matching for "my share" | Automates what can be entered by hand while labelling | |
| Later | Other banks' files (CFCAL CSV, Fortuneo PDF), auto-detect bank/account | Low volume, manual entry works meanwhile | |
| Later | Email context; auto-labelling trained on validated labels | Needs a labelled history first | |
| Later | MCP interface for agent-assisted labelling (optional, private, authenticated) | Faster labelling from an agent; the web flow stays complete without it | |

Dependencies: analysis needs labels; savings rate needs transfer detection; net worth needs
balances. PDF backfill depends on riskiest assumption 3 (statements add up): test it before
speccing.
