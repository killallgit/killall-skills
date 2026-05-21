---
name: worktree-cleanup
description: >
  Automated git worktree hygiene. Prunes dead references, evaluates remaining
  worktrees for merge safety, removes clean/merged ones automatically, and lists
  force-delete candidates for manual review. Never force-deletes without explicit
  user confirmation.
---

# Worktree Cleanup

Automated worktree hygiene. Runs in four phases — no prompt for prune/safe removal; force-delete candidates are listed only, never deleted automatically.

## Phase 1 — Prune stale references

Always run first. Removes entries whose working directory no longer exists on disk:

```bash
git worktree prune -v
```

Output any pruned paths.

## Phase 2 — Inventory remaining worktrees

```bash
git worktree list --porcelain
```

For each worktree (skip the main/bare one):
- Extract: `worktree` path, `HEAD` commit, `branch` ref
- Derive branch name: strip `refs/heads/` prefix

Build a table:

| Path | Branch | Status |
|------|--------|--------|

## Phase 3 — Evaluate each worktree

For each non-main worktree, run these checks in order. Stop at first disqualifier.

### Check A — uncommitted/staged changes

```bash
git -C <path> status --porcelain
```

Non-empty output → **FORCE-DELETE candidate** (has local changes). Record and skip further checks.

### Check B — commits not in main

```bash
git log main..<branch> --oneline
```

Non-empty → may have unmerged work. Continue to Check C to see if PR handled it.

### Check C — PR state (if gh available)

```bash
gh pr list --head <branch> --json number,state,mergedAt --limit 1
```

- `state: MERGED` → PR merged, commits are accounted for → **SAFE to remove**
- `state: CLOSED` (not merged) + unmerged commits → **FORCE-DELETE candidate** (abandoned with commits)
- No PR + unmerged commits → **FORCE-DELETE candidate**
- No PR + no unmerged commits → **SAFE to remove** (branch fully reachable from main)

### Check D — branch merged into main (no gh / fallback)

```bash
git merge-base --is-ancestor <branch> main && echo "merged" || echo "not merged"
```

`merged` → **SAFE to remove**. Otherwise → **FORCE-DELETE candidate**.

## Phase 4 — Act on results

### Safe removals — execute automatically

For each SAFE worktree:

```bash
git worktree remove <path>
git branch -d <branch>   # only if branch still exists and is fully merged
```

Print each removal as it happens:
```
removed: <path>  (<branch>)
```

### Force-delete candidates — list only, do not delete

Print a table and stop:

```
Worktrees requiring force-delete (unmerged commits or local changes):

  PATH                    BRANCH              REASON
  /path/to/worktree       feat/my-branch      uncommitted changes
  /path/to/worktree2      feat/other-branch   unmerged commits, no PR

To remove:
  git worktree remove --force <path>
  git branch -D <branch>
```

**Do not run force-delete commands.** User must review and run manually or confirm explicitly.

## Error handling

- If `gh` not installed or not authenticated, skip Check C and fall back to Check D.
- If `main` branch doesn't exist, try `master` then ask the user.
- If a worktree is in detached HEAD state, flag as FORCE-DELETE candidate with reason "detached HEAD".
- If `git -C <path>` fails (path missing but not pruned), skip — prune should have caught it.

## Summary output format

End with a compact summary:

```
Worktree cleanup complete.
  Pruned (stale references):  N
  Removed (safe):             N
  Force-delete candidates:    N  (listed above — manual action required)
```
