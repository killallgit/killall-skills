---
name: setup-agents-md
description: Set up and review root AGENTS.md and CLAUDE.md. Merge shared instructions from both into AGENTS.md without losing unique or tool-generated guidance, simplify the combined instructions, verify them against the repo, and make CLAUDE.md import AGENTS.md with @AGENTS.md. Create missing files as needed. Use for "setup agents md", "check the agent docs", "check project", "dedupe CLAUDE.md and AGENTS.md", or /setup-agents-md.
---

# Setup AGENTS.md

Leave one concise, accurate set of shared instructions in `AGENTS.md` and a
`CLAUDE.md` that imports it. This is a review of the combined instructions,
not a template replacement. Preserve unique guidance before removing any text.

## Target shape

- **`AGENTS.md` holds shared instructions:** commands, repository layout,
  conventions, workflow, and tool guidance that every agent needs.
- **`CLAUDE.md` imports it** with `@AGENTS.md` on its own line outside code
  blocks, followed only by Claude-specific instructions such as hooks,
  subagents, slash commands, and `.claude/` settings. Just the import is fine.
- **Imports point one way.** Do not put `@CLAUDE.md` in `AGENTS.md` or create
  an import cycle. Other agents read `AGENTS.md` as plain text.

## 1 — Read before writing

Work at the repository root (`git rev-parse --show-toplevel`). Check the Git
status and read existing `AGENTS.md` and `CLAUDE.md` completely, including
existing local changes. Follow their imports and linked instruction documents
within scope, tracking visited paths to avoid cycles. Do not overwrite either
file with a standard template.

An import is an `@path` outside code spans and fenced blocks; a prose mention
like "see AGENTS.md" is not an import. Report missing import targets.

- **Both files exist:** reconcile their full contents, even if the import
  already exists. Tools may have appended new instructions to either file.
- **Only `CLAUDE.md` exists:** create `AGENTS.md` from its shared instructions
  before replacing that text with the import. Keep Claude-specific text.
- **Only `AGENTS.md` exists:** review and simplify it, then create `CLAUDE.md`
  containing `@AGENTS.md`.
- **Neither exists:** create concise `AGENTS.md` guidance grounded in the
  repository's documentation and configuration, plus `CLAUDE.md` containing
  `@AGENTS.md`. Do not invent commands, conventions, or policies.
- **Either is a symlink:** inspect the resolved target before writing. Do not
  replace the link or write a self-import into a shared target. If separate
  files are needed, explain the proposed link conversion and confirm first.

## 2 — Reconcile and simplify

Account for every distinct instruction in both files and their referenced
guidance before editing. For each, identify its destination: shared guidance
in `AGENTS.md`, Claude-specific guidance in `CLAUDE.md`, an existing referenced
document, or a proposed removal that needs confirmation.

- Move shared instructions found only in `CLAUDE.md` into `AGENTS.md` first.
  Adding an import alone does not preserve the text it replaces.
- Preserve unique tool-generated sections, setup notes, commands, caveats,
  and integration instructions, even when only one file contains them.
  Generated text is not automatically redundant or disposable. Preserve
  required markers and placement; if a tool requires a section in `CLAUDE.md`,
  leave it there and keep any shared requirements accessible from `AGENTS.md`.
- Review all of `AGENTS.md`, not just passages copied from `CLAUDE.md`.
  Combine repeated rules, group related guidance, and shorten wording while
  preserving requirements, exceptions, command arguments, and scope.
- Deduplicate exact matches and equivalent instructions. Similar wording with
  different constraints is not a duplicate; preserve both pending resolution.
- Keep useful referenced documents rather than blindly inlining them. Shared
  instructions must remain accessible to agents that do not expand Claude
  imports; use explicit readable paths or Markdown links in `AGENTS.md`.
- Reverse an `@CLAUDE.md` dependency by preserving the shared guidance in
  `AGENTS.md`, removing the reverse import, and adding `@AGENTS.md` to
  `CLAUDE.md`. Check the full import graph for cycles.

Lossless moves, deduplication, and meaning-preserving simplification may be
applied directly. Batch anything that changes or drops a requirement for one
confirmation: conflicting rules, stale instructions, uncertain generated
sections, or proposed policy changes. Keep unresolved guidance intact and
report it; do not silently choose one version.

## 3 — Verify accuracy

Treat every checkable claim in the combined instructions as something to
verify, including claims already in `AGENTS.md`:

| Claim | Evidence |
| --- | --- |
| Commands | `package.json` scripts, Makefile, justfile, pyproject.toml, CI workflows |
| Paths and layout | tracked files and actual working-tree paths |
| Tool and runtime versions | lockfiles, .tool-versions, .nvmrc, go.mod, rust-toolchain.toml |
| Named scripts, skills, agents | their actual definitions and names |
| Branching, CI, release process | workflows, repository docs, remote default branch |

Confirm commands exist; do not execute them merely to check documentation.
Where instructions disagree, use repository evidence; ask when it cannot
decide. Preferences and style rules are not disproved by repository evidence.
Do not remove them just because they cannot be mechanically verified.

## 4 — Prove preservation and report

Compare the final files with the originals and the instruction inventory:

- Every unique instruction is preserved in its destination or accessible
  reference, or its change/removal was explicitly approved.
- Tool-generated sections and required markers remain intact unless their
  removal or alteration was approved.
- `CLAUDE.md` has a working `@AGENTS.md` import, not a mention or fenced example.
- There are no broken references, reverse imports, or import cycles.
- The combined `AGENTS.md` is concise, internally consistent, and reviewed
  against the repository, not merely populated with moved text.

If an unresolved conflict prevents this target shape, report it rather than
claiming success. Re-read the final files; do not infer preservation from a
smaller diff or fewer lines. A second pass should need no edits unless inputs
changed.

Leave changes uncommitted. Finish with `git diff --stat -- AGENTS.md CLAUDE.md`,
note newly created files (untracked files do not appear in that diff), and give
one line per file describing what was merged, simplified, or retained. List
unresolved questions and the number of claims verified. If no edits are
needed, say the docs are clean and report the verification count.

## Scope

Root `AGENTS.md` and `CLAUDE.md` and the guidance they reference only. Nested
agent files, `CLAUDE.local.md`, and user-level configuration are out of scope.
Do not modify imported or linked documents without approval; report issues in
them instead. Do not add speculative rules or unrelated documentation.
