---
name: end-session
description: Bring this session's branch up to date, land or discard its work, and archive the session.
disable-model-invocation: true
---

# End session

Close out the work this session did. The user asks one question at most: whether
a PR is required. When a `caveman` skill is available in this session, invoke it
first.

## 1. Sync

`git fetch --prune`. Fast-forward every local branch that tracks an upstream and
can fast-forward. Rebase this session's branch onto the default branch. Resolve
mechanical conflicts; for a conflict that needs judgement, abort the rebase,
report it, and stop.

## 2. Classify

Compare this branch's commits and uncommitted changes with the default branch.
Use `git cherry`, tree comparison, and file content, so work that landed through
a squash or a later rewrite counts as landed. The result is one of:

- **Superseded**: nothing here still belongs on the default branch. Go to step 4.
- **Open PR**: the branch already has an open PR. Push with
  `--force-with-lease` and go to step 4.
- **Needs landing**: some change still belongs on the default branch. Go to step 3.

## 3. Ask

List the changes that need landing in a few lines, then ask whether a PR is
required.

- **Yes**: commit any uncommitted changes, push, and open the PR with `gh pr create`.
  Go to step 4 without further interaction.
- **No**: leave the branch and worktree in place. Report and stop.

## 4. Archive

For superseded work, remove this session's worktree and delete its local branch.
For a PR, keep both. Then archive this session with the host's session tool. When
the host has none, tell the user the session is ready to archive.
