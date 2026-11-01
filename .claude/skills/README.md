# Skills

Project skills for Claude Code. `product-brainstorming`, `write-spec` and `roadmap-update` are
adapted from [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins)
(Apache-2.0, see `LICENSE-knowledge-work-plugins`) and customized for this repo.

`architecture-diagram` is home-grown.

The adapted skills are vendored, not installed as a plugin: like any dependency, they are pinned, and
updates are reviewed in a PR instead of applied automatically.

**Pinned upstream commit:** `a518709` (2026-03-18).

To update: open
[the upstream diff](https://github.com/anthropics/knowledge-work-plugins/compare/a518709...main),
look at changes under `product-management/skills/`, merge the useful ones by hand, then bump
the SHA here and in each skill's attribution note.
