---
name: check-agent-docs
description: Review and clean up a project whose root has both AGENTS.md and CLAUDE.md — shared instructions live once in AGENTS.md, CLAUDE.md imports them with `@AGENTS.md` instead of repeating them, and every checkable claim in either file still matches the repo. Use when the user says "check the agent docs", "check project", "dedupe CLAUDE.md and AGENTS.md", or invokes `/check-agent-docs`. Does nothing unless both files exist.
---

# Check Agent Docs

A project that serves more than one coding agent keeps two instruction files at
its root: `AGENTS.md`, read by Codex and most other agents, and `CLAUDE.md`,
read by Claude Code. Left alone they drift — the same rules pasted into both,
edited in one, until they contradict each other and the code.

This is a quick pass. It leaves one copy of every instruction and removes what
is no longer true.

## Target shape

- **`AGENTS.md` holds everything shared** — commands, layout, conventions,
  anything every agent should follow.
- **`CLAUDE.md` imports it** with `@AGENTS.md` on its own line, followed only
  by what is specific to Claude Code: hooks, subagents, slash commands,
  `.claude/` settings. A `CLAUDE.md` that is nothing but the import is correct.
- **The import points one way.** Claude Code expands `@path` imports; other
  agents read `AGENTS.md` as plain text, so `@CLAUDE.md` inside `AGENTS.md`
  hands them a dead string instead of the instructions.

## 0 — Gate

From the repo root (`git rev-parse --show-toplevel`):

```bash
ls -la AGENTS.md CLAUDE.md
```

- **Either file missing** → say which one exists and stop. There is nothing to
  reconcile. Do not create the missing file.
- **One is a symlink to the other** → it is one file, so there is no
  duplication and no import to add. Skip to step 3.

## 1 — Read

Read both files in full, plus anything either already imports. An import is a
`@path` outside code spans and fenced blocks — Claude Code ignores it inside
them — and a prose mention like "see AGENTS.md" is not one.

## 2 — Structure

- **Import.** Flag `CLAUDE.md` with no `@AGENTS.md`, an import stuck inside
  code, `@CLAUDE.md` in `AGENTS.md`, or the two importing each other.
- **Duplication.** Anything in `CLAUDE.md` that `AGENTS.md` already says,
  verbatim or paraphrased. Through the import it loads twice, and the second
  copy is where drift starts. Take the exact matches first:

  ```bash
  comm -12 <(sed 's/^[[:space:]]*//;s/[[:space:]]*$//' AGENTS.md | grep -Ev '^$|^#|^```|^---$' | sort -u) \
           <(sed 's/^[[:space:]]*//;s/[[:space:]]*$//' CLAUDE.md | grep -Ev '^$|^#|^```|^---$' | sort -u)
  ```

  Then read for restatements that no line match catches. A heading shared by
  both files is fine; a shared instruction is not.
- **Placement.** Shared instructions that live only in `CLAUDE.md` belong in
  `AGENTS.md`, or every other agent misses them. Claude-only instructions in
  `AGENTS.md` belong in `CLAUDE.md`.

## 3 — Accuracy

Every checkable statement in either file is a claim to verify, not a fact:

| Claim | Check against |
| --- | --- |
| Commands (`npm run x`, `make y`, `uv run z`) | `package.json` scripts, `Makefile`, `justfile`, `pyproject.toml`, CI workflows |
| Paths and layout | `git ls-files` |
| Tool and runtime versions | lockfiles, `.tool-versions`, `.nvmrc`, `go.mod`, `rust-toolchain.toml` |
| Named files, scripts, skills, agents | that each exists under that name |
| Branching, CI, release process | `.github/workflows/`, the remote default branch |

Confirm a command exists; do not run it. Where the two files disagree, the repo
decides; if it cannot, ask. Preferences and style rules cannot be wrong against
the repo — leave them alone.

## 4 — Report

One table, most consequential first:

| # | File | Finding | Fix |
| --- | --- | --- | --- |
| 1 | CLAUDE.md | no `@AGENTS.md` import | add it at the top |
| 2 | CLAUDE.md | Testing section repeats AGENTS.md | delete from CLAUDE.md |
| 3 | AGENTS.md | `npm run typecheck` — no such script | `npm run check:types` |

Nothing found → print
`Agent docs clean — CLAUDE.md imports AGENTS.md, no duplication, N claims verified.`
and stop.

## 5 — Clean up

Split the fixes by whether they change what an agent is told:

- **Apply directly** — lossless moves: add the import, delete text from
  `CLAUDE.md` that `AGENTS.md` already says, move shared instructions into
  `AGENTS.md` and Claude-only ones into `CLAUDE.md`. What Claude Code loads is
  the same afterwards. Two copies that differ are not a lossless delete.
- **Confirm first** — anything that changes or drops an instruction: correcting
  a stale command or path, removing a claim the repo contradicts, choosing
  between two copies that differ. Present them as one batch for a single
  confirmation and skip whatever the user declines.

To reverse an `@CLAUDE.md` import, move the shared content from `CLAUDE.md`
into `AGENTS.md`, delete the `@CLAUDE.md` line, and add `@AGENTS.md` to
`CLAUDE.md`.

Leave the changes uncommitted. Finish with
`git diff --stat -- AGENTS.md CLAUDE.md` and one line per file saying what
changed.

## Rules

- **Root files only.** Nested `AGENTS.md` or `CLAUDE.md`, `CLAUDE.local.md`,
  and user-level config are out of scope.
- **Not an edit pass.** Do not reword, reorder, or restyle beyond what
  deduplication and the confirmed fixes require.
