---
description: Put constraints in auto-loaded rule files and descriptions in on-demand docs
globs: ["**/*.md"]
---
# Agent Doc Placement

Agent-facing documentation lives in two different places for two different
reasons. Putting a file in the wrong one is how a repo ends up feeding stale
facts to every agent session with rule-level authority.

## The test

**Can a code change violate this sentence?**

- Yes — it is a **rule**. It constrains what the code may become.
- No — it is a **description**. It reports what the code currently is.

"Every list command implements the `Adapter` trait" is a rule; code can break
it. "There are eleven top-level commands" is a description; code can only make
it out of date.

## Where each goes

**Rules** go in the host's auto-loaded instruction directory (`.claude/rules/`,
`.cursor/rules/`, or the agent instruction file itself). These are injected into
every matching session, so they must be small, normative, and stable.

**Descriptions** go under `docs/` with no path-glob frontmatter. Agents read
them on demand, when the task actually calls for orientation. A stale
description that is read deliberately is a minor cost; the same file
auto-injected into every session is a persistent source of wrong answers.

Never give a descriptive file path-glob frontmatter. That is the specific
mistake this rule exists to prevent: a human-facing architecture map placed in
the rules directory, silently loaded as law, drifting one PR at a time.

## Sort by churn rate

Split docs by how fast their content changes, not by topic. A single file that
mixes a stable error hierarchy with a per-PR module tree will be judged by its
fastest-moving section — and once one part is visibly wrong, agents and humans
stop trusting all of it.

| Churn | Typical home |
|---|---|
| Per-PR | code, and generated reference output |
| Per-feature | `docs/` surface or API notes |
| Per-decision, append-only | `docs/adr/` |
| Rare | `docs/` architecture overview |
| Rare, normative | auto-loaded rule files |

## One owner per fact

When two files state the same fact, neither gets reviewed and both drift. Give
every fact exactly one owner and have the others link to it. A fact that only
one file can get wrong is a fact review can catch.

## Make drift mechanical where you can

Prefer checks over discipline. A build-step script that asserts every source
path mentioned in the docs still exists will catch a deleted directory the day
it happens; a convention that says "keep the docs updated" will not.
