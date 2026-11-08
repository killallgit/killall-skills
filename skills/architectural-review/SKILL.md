---
name: architectural-review
description: Review a codebase's architecture. Finds hotspots in git history, walks them for friction, writes an HTML report of deepening candidates with before/after diagrams, proposes glossary terms, and suggests beads for the work. Words after the command name a direction (a module, a subsystem, a pain point).
disable-model-invocation: true
argument-hint: "[module, subsystem, or pain point]"
---

# Architectural review

Find where the architecture causes friction and name it in a shared language,
so code gets easier to change, test, and navigate. When a `caveman` skill is
available, invoke it first.

Read [vocabulary.md](references/vocabulary.md) first. Use its terms exactly.

## 1. Scope

Take the user's direction if they gave one. Otherwise:

```
uv run --python 3.12 <skill-dir>/scripts/hotspots.py [--since "6 months ago"]
```

Hotspots are where deepening pays off soonest; change-coupled pairs with no
code dependency are hidden seams or leaks. Treat both as probabilities.

## 2. Read

Read `GLOSSARY.md` (or `GLOSSARY-MAP.md`), `ARCHITECTURE.md`, and the ADRs in
`docs/adr/` that touch the scope. Don't re-litigate an ADR. A missing file is a
finding.

## 3. Explore

Dispatch a fresh-context subagent on the scope with the hotspot output and the
paths of `vocabulary.md` and the glossary. It reports friction with
`path:line` evidence, not fixes. Re-read every cited spot yourself and drop
what you can't confirm. Keep only candidates that pass the deletion test.

## 4. Report

Write findings JSON to the OS temp dir in the shape in
[report.md](references/report.md), then:

```
uv run --python 3.12 <skill-dir>/scripts/render_report.py <findings.json>
```

It prints the report path, then the bead commands. Open the report and give
the user its path. Name modules with glossary terms. Don't design interfaces
yet. Ask: "Which candidates should we pursue?"

## 5. Follow through

- **Beads**: with `.beads/` and `bd` present, run the printed commands for the
  chosen candidates only, after the user confirms. Otherwise list them as tasks.
- **Glossary and ADRs**: follow [docs.md](references/docs.md) when a term
  settles or a candidate is rejected for a reason a future review would need.
- **Interfaces**: design it twice. Sketch two interfaces for the deepened module
  (parallel subagents when available) and compare depth, locality, and which
  tests survive.
