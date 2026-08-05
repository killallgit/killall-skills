---
name: git-janitor
description: >
  Systematically clean and report on a git repo. Auto-prunes worktrees and dead
  refs, removes merged worktrees, inventories local branches, delegates per-branch
  investigation to a fast read-only subagent, prints a compact keep/delete table,
  then interactively reviews each branch and deletes only what you confirm. Use
  when the user wants to clean up branches/worktrees, "prune the repo", garbage-
  collect stale branches, or audit what unmerged branches contain.
---

# git-janitor

Interactive repo hygiene, run from the main thread (it must prompt you, so it
cannot run as a pure subagent). The heavy per-branch investigation is delegated
to the fast `git-janitor-investigator` agent (haiku); decisions and deletions
stay here, behind your confirmation.

## Safety rules (always)

- **Local only.** Never `push`, `fetch`, or delete remote branches without a
  separate explicit confirmation.
- Never delete the **default** or **currently checked-out** branch.
- `git branch -d` (safe, merged-only) may run after confirmation. `git branch -D`
  (force) and `git worktree remove --force` run **only** on explicit per-item
  confirmation — never in bulk, never unprompted.

## Phase 0 — Preflight

```bash
git rev-parse --is-inside-work-tree            # abort if not a repo
git branch --show-current                      # current branch — never delete
git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null  # -> default
```

Default branch = origin/HEAD target; else `main`, else `master`; else ask. Call
it `<default>`.

## Phase 1 — Worktrees (auto)

```bash
git worktree prune -v                           # drop dead references
git worktree list --porcelain
```

For each non-main worktree:
- Dirty (`git -C <path> status --porcelain` non-empty) → **candidate** (list, don't remove).
- Detached HEAD → **candidate** with reason `detached HEAD`.
- Clean with a merged PR (`gh pr list --head <branch> --json number,state,mergedAt --limit 1`) → auto `git worktree remove <path>`, then safe-delete its branch with `git branch -d`.
- Clean AND branch merged (`git merge-base --is-ancestor <branch> <default>`) → auto `git worktree remove <path>`, then `git branch -d <branch>`.
- Closed-unmerged PR, unmerged commits, missing PR, or failed inspection → **candidate** with the exact reason (list, don't force-delete).

Print every automatic removal as it happens. For candidates, retain the path,
branch, and reason for the Phase 4 report. Never infer that a clean worktree is
safe merely because it has no uncommitted files.

## Phase 2 — Branch inventory

```bash
git branch --merged <default>    # safe-delete bucket (minus <default> & current)
git branch --no-merged <default> # investigation bucket
```

Merged branches → bulk safe-delete bucket. Unmerged → investigate in Phase 3.

## Phase 3 — Investigate unmerged (delegate, parallel, fast)

For each unmerged branch, spawn **`git-janitor-investigator`** via the Agent tool
— all in one message so they run in parallel. Pass the branch and `<default>`.
Each returns one table row.

If that agent is unavailable (non-Claude host), run its read-only protocol inline
instead, or spawn a read-only `Explore`/general-purpose agent with `model: haiku`
and the same instructions. Same rows either way.

## Phase 4 — Report

Render one compact table (rows from Phase 3 under this header):

```
| Branch | Age | Ahead | Files | PR | Rec | Summary |
|--------|-----|-------|-------|----|-----|---------|
```

Then list separately:
- **Merged (safe-delete):** the Phase 2 merged branches.
- **Worktree candidates:** dirty/unmerged worktrees from Phase 1 (manual).

## Phase 5 — Interactive review

1. Merged branches: offer **bulk safe-delete** (`git branch -d <b>` each — fails
   harmlessly if not actually merged). One confirmation covers the batch.
2. Unmerged branches: ask whether to review each. For each, use AskUserQuestion
   (default = its `Rec`): **Keep** / **Delete**. On Delete, confirm, then
   `git branch -D <b>`.
3. Worktree candidates: print the `git worktree remove --force <path>` commands
   for the user to run; do not execute them.

Skip current/default branches entirely.

## Phase 6 — Summary

```
git-janitor complete.
  Worktrees:  pruned N · removed N · candidates N
  Branches:   merged-deleted N · force-deleted N · kept N
```
