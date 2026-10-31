# Banking: product discovery

> Brainstorm notes, 2026-10-31. They cover **what** to analyse and **which data** is needed;
> technical choices belong in the specs (GitHub issues).

## Problem
Several banks and accounts, no cross-account view, and statements are the only reliable
export. Shared costs with my partner are tracked in a separate Google Sheet (fed by a Google
Form). I want labelled operations with a pleasant labelling flow, labels stored safely, and
eventually auto-labelling that I only validate.

## What the analysis must answer
1. **Where my money goes:** spending per category per month, across all accounts, counting
   *my share* of shared costs (rent paid 100%, owed 50%).
2. **Savings rate:** (income − real spending) / income. Transfers to savings, PEA or life insurance
   count as saved, not spent.
3. **Net worth trend:** total value of all accounts over time, including closed ones while
   they were open.
(Settling up with the partner is *not* a goal: the sheet is only used for my share and context.)

## Accounts and inputs (facts from user)
| Bank | Accounts | Volume | Available input | History need |
| --- | --- | --- | --- | --- |
| Banque Postale | 1 current | high | CSV, **last 90 days only**; PDF statements | back to end 2024 |
| Banque Postale | 3 savings (2 open, 1 recently closed) | low | CSV / PDF statements | back to end 2024 |
| CFCAL | 1 savings | low | CSV | back to end 2024 |
| Fortuneo | 1 PEA (new) | low | PDF statements (CSV unknown) | since opening |
| Goodvest | life insurance | 1–2 ops/month | none: manual entry is fine | manual |

Reframe: only the Banque Postale current account is high-volume. The 90-day CSV limit means
older history comes from PDF statements, and a missed export window loses data → the app must
show how fresh each account's data is.

## Data needed
- **Accounts:** bank, type (current, savings, PEA, life insurance), opened/closed dates. User
  can declare a new account or mark one closed.
- **Operations:** account, date, amount, bank description, origin (file import or manual).
  User can always add or edit operations by hand.
- **Balances:** per account over time (from statements or entered by hand), for net worth
  and to check that imports are complete.
- **Labels:** category, optional tags, "my share" amount, transfer flag (own account to own
  account), who/what confirmed it (suggested vs validated).
- **Context evidence** (optional, can be added later): shared-sheet rows, receipt emails.
  Bank descriptions alone are often too thin (`CB PAYPAL`, `PRLV SEPA …`).

## Labelling: the core experience
- Each operation is shown with a suggested label and whatever context is available. The user
  accepts or fixes it in one step. Validated labels are stored safely and become the training
  set for future auto-labelling.
- **Categories:** start from the shared sheet's categories; the app owns its own editable list
  (add, rename, merge) and a mapping from sheet categories.
- **Proposed split: category vs tag.** One-category-per-holiday-location is really *context*
  ("Holiday Lisbon 2026"), not *type of expense* (food, lodging, transport). Keep a small,
  stable category list plus free tags, so summaries stay comparable and auto-labelling learns a
  stable target. To confirm in the spec.
- **Shared-sheet matching:** dates and amounts don't match exactly (form filled later, cash).
  Matching is approximate and confirmed by the user; sheet rows with no bank operation
  (cash, paid by partner) are normal.
- **Emails:** possible later source of context for opaque operations. Not in the first slices.

## Long-term vision for import
Drop any statement file (CSV, PDF, …) → the app recognises the bank and account, extracts the
operations, skips duplicates from overlapping files, and suggests labels. Manual entry remains
available for everything.

## Candidate features (for the roadmap)
1. **Accounts:** declare, list, close.
2. **Banque Postale current-account CSV import** with duplicate detection across overlapping
   exports, and a "data last updated" indicator per account.
3. **Manual operations and balances** (Goodvest, corrections, cash).
4. **Labelling flow:** categories, tags, rule-based suggestions ("same as last time"),
   review queue.
5. **Internal transfer detection** so moves between own accounts aren't counted as spending.
6. **Shared-sheet matching** → my share.
7. **Monthly analysis:** the 3 questions above.
8. **History backfill from PDF statements** (Banque Postale accounts back to end 2024).
9. **Other banks' files** (CFCAL CSV, Fortuneo PDF), then auto-detecting bank and account
   from any dropped file.
10. **Later:** email context; auto-labelling model trained on validated labels.

Decided: first slice ("Now") = items 1, 2 and 4 for the Banque Postale current account.

## Riskiest assumptions (with cheapest test)
1. *Rules label most operations.* Label one month by hand; count how many a "same
   description → same category" rule gets right. That sets the bar auto-labelling must beat.
2. *Overlapping CSVs can be deduplicated reliably.* Export two overlapping windows and compare.
3. *PDF statements contain everything needed.* Check that 2–3 statements' operations add up
   to their opening/closing balances.
4. *Context sources explain opaque operations.* Take 20 operations you can't identify and
   see how many the shared sheet (or emails) explains.
5. *Exports happen within 90 days.* Mitigated by the freshness indicator.

## Open questions
- ~~Labelling flow: where and on which device~~ Resolved in
  [#13](https://github.com/machbry/autoquest/issues/13): desktop browser, keyboard only.
- Fortuneo PEA: CSV export available?
- ~~Category vs tag split~~ Confirmed in [#13](https://github.com/machbry/autoquest/issues/13):
  categories are the type of expense, context goes in tags.

## Next steps
Done: roadmap in the [app README](../README.md), specs
[#12](https://github.com/machbry/autoquest/issues/12) and
[#13](https://github.com/machbry/autoquest/issues/13).
