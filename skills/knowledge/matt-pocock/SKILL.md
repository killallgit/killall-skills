---
name: matt-pocock
description: Point at the upstream mattpocock/skills set, which this repo defers to entirely for planning, implementation, review, and architecture work — to-prd, to-issues, setup-planning, tdd, code-review, diagnose, triage, wayfinder, prototype, research, handoff, codebase-design, domain-modeling, improve-codebase-architecture, resolving-merge-conflicts. Use when one of those names is invoked but missing, or when installing them.
---

# Matt Pocock's Skills

Fifteen of this repo's skills were forks of
[mattpocock/skills](https://github.com/mattpocock/skills). Carrying the fork
bought nothing and shipped every skill twice for anyone who had both installed,
so they were removed — this repo defers to upstream for the whole
plan → implement → review → architect workflow and keeps only what upstream has
no answer for.

## Install

Two routes, two philosophies. **Pick one** — installing both leaves you with
every skill twice, which is the duplication this skill exists to prevent.

A managed, read-only bundle that updates when upstream ships (Claude Code only):

```bash
claude plugins install mattpocock-skills
```

Editable files you own, on any agent — the same route this repo uses:

```bash
npx skills@latest add mattpocock/skills
```

Then run `setup-matt-pocock-skills` once per repo. It owns the issue tracker
choice, the triage label vocabulary, and where docs get written — everything
this repo's `setup-planning` fork used to write into
`docs/agents/issue-tracker.md`. Take it with the rest; the planning, triage, and
implementation skills read the config it produces.

## Name map

| Removed from here | Upstream name |
| --- | --- |
| `architecture/codebase-design` | `codebase-design` |
| `architecture/domain-modeling` | `domain-modeling` |
| `architecture/improve-codebase-architecture` | `improve-codebase-architecture` |
| `engineering/code-review` | `code-review` |
| `engineering/diagnose` | `diagnosing-bugs` |
| `engineering/resolving-merge-conflicts` | `resolving-merge-conflicts` |
| `engineering/tdd` | `tdd` |
| `experimental/prototype` | `prototype` |
| `knowledge/handoff` | `handoff` |
| `knowledge/research` | `research` |
| `planning/setup-planning` | `setup-matt-pocock-skills` |
| `planning/to-prd` | `to-spec` |
| `planning/to-issues` | `to-tickets` |
| `planning/triage` | `triage` |
| `planning/wayfinder` | `wayfinder` |

Upstream also ships skills this repo never had — `grilling`, `wizard`,
`writing-for-agents`, `implement`, `ask-matt` among them. Browse the set before
assuming a gap.

## What changes in practice

The forks were rewritten to be host-agnostic and to read a repo-local planning
contract. Upstream reads its own:

| The forks read | Upstream reads |
| --- | --- |
| `docs/CONTEXT.md` | `CONTEXT.md` |
| `docs/out-of-scope/` | `.out-of-scope/` |
| `docs/agents/issue-tracker.md` | the tracker config `setup-matt-pocock-skills` writes |

A repo already configured by the old `setup-planning` will not be read correctly
by the upstream skills. Re-run `setup-matt-pocock-skills` there and move any
`docs/CONTEXT.md` and `docs/out-of-scope/` content to the paths above.

Several upstream skills carry `disable-model-invocation: true` (`triage`,
`wayfinder`, `to-spec`, `to-tickets`, `implement`). They run only when a human
invokes them; the forks had no such gate, so anything that relied on automatic
invocation now needs an explicit call.

## Still owned here

What is left has no upstream counterpart: `project-planner` (the pre-spec
scoping interview), `git-janitor`, `review-library-usage`, `wait-for-action`,
`setup-wiki`, `wiki`, and `create-extension`.
