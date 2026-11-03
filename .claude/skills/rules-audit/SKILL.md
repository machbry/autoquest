---
name: rules-audit
description: Audit the autoquest code against the rules of its CLAUDE.md files that tests can't check (judgement rules) and report the violations. Read-only: it never changes code or files issues. Use for the monthly audit (GitHub Actions) or on demand, for the whole repo or one app.
argument-hint: "[app]"
---

# Rules Audit

Checks that the code really follows the `CLAUDE.md` rules and reports the violations.
Read-only: it never changes the code and never files issues. The user reviews the
findings and writes the issues they want with `/write-spec`.

## 1. Read the rules
- Glob every `CLAUDE.md` (root and `apps/*/`), and read each one with the files it imports
  (`@path` lines).
- The root `CLAUDE.md` **Rule enforcement** section lists the rules checked by tests and
  tools. Skip them: CI already enforces them. Audit everything else.

## 2. Review the code
Scope: the whole repo, or only `apps/<app>/` when an app is given. Read the code, tests,
docs, workflows and Docker/Terraform files the rules apply to. Typical judgement rules:
- comments explain *why*, not *what*; docs are concise and match the code;
- no speculative abstractions, dead code or premature generalization;
- tests through public interfaces, not mirroring the implementation; required tests exist
  (integration per feature, e2e per app, regression per bug fix);
- layer responsibilities and CRUD naming conventions (beyond `test_layers.py`);
- invariants held by database constraints; services translate repository errors;
- logs leaking personal or banking data; personal data stored, collected or committed;
- architecture docs (`docs/architecture.*`) in line with the components.

Report only clear violations you can point to, not style preferences. Group them by rule
and scope (one app, or `core` for repo-wide files). For each group keep:
- the rule, quoted verbatim, and the `CLAUDE.md` file it comes from;
- every offending location as `path:line`;
- one sentence on why each location breaks the rule.

**Never quote code contents, data or log output:** rules and locations only.

## 3. Check the rules themselves
Flag as their own groups:
- contradictions between `CLAUDE.md` files (an app file may override the root only where
  it says so);
- stale rules: the code departs from a rule on purpose, consistently, so the rule should
  change, not the code;
- rules naming files, tools or commands that no longer exist.

## 4. Report
Group order: the most serious first (security and data leaks, then broken invariants,
then the rest). Show each group as:

```markdown
### <rule, quoted verbatim>
<source CLAUDE.md> · <scope>
- `path:line`: why it breaks the rule
```

With no violation, say so in one line. In CI, return the same groups as the structured
output the workflow asks for (`findings`, empty when there are none): the workflow prints
them and fails the run when there is at least one.
