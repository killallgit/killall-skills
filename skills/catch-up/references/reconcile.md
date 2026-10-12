# Reconcile

Account for every dangling change in the current checkout before the summary is
written, so the user resumes from a clean, true state. A **dangling** change is
anything not yet on the default branch or an open PR: staged, unstaged, and
untracked files (ignored files excluded), plus local commits the upstream lacks.

Scope is this checkout and its branch. Other worktrees and stale branches belong
to `git-janitor`.

## 1. Fetch and resolve the default branch

`git fetch --prune`. Resolve the default branch from `origin/HEAD`, else
`gh repo view --json defaultBranchRef`. Compare against `origin/<default>`, not
the local copy, which may be behind.

## 2. Classify each dangling change

Group changes by purpose, not by file: one fix spread across three files is one
group. Read the content of every group before classifying it. Each group lands
in exactly one bucket, with the evidence noted:

- **Landed**: the result is already on `origin/<default>`. Evidence is content:
  the file matches `git show origin/<default>:<path>`, the hunk already appears
  there, or `git cherry` marks the commit as upstream. Work landed through a
  squash or a later rewrite counts as landed.
- **Scratch**: throwaway by nature: debug prints, temp and log files, stray
  build output, an editor's backup files.
- **PR work**: continues an open PR authored by the current `gh` user. Evidence
  is overlap: the PR's diff touches the same files or the same feature, and the
  change reads as the next step of that PR's description.
- **Unclaimed**: everything else, including any group whose bucket rests on a
  guess. New work with no PR is unclaimed.

## 3. Act on each bucket

- **Landed** and **Scratch**: discard with `git restore --staged --worktree`
  and `git clean` on exactly those paths. This cannot be undone, so the evidence
  from step 2 must be content you read, never a name or a timestamp alone.
- **PR work** on the current branch: commit it with a message describing the
  change.
- **PR work** for another PR: export the group with `git diff` (add untracked
  files with `git add -N` first), apply it in a worktree checked out on that
  PR's branch (reuse an existing one, else `git worktree add` a temporary one
  and remove it afterwards), commit, and push. Once the push succeeds, discard
  the group here.
- **Unclaimed**: leave in place, untouched.

## 4. Sync the branch

- **On the default branch**: `git merge --ff-only origin/<default>`.
- **On a branch whose PR merged**: leave it; report that it landed.
- **On any other branch**: rebase onto `origin/<default>` with `--autostash` so
  unclaimed changes ride along. Resolve mechanical conflicts. For a conflict
  that needs judgement, run `git rebase --abort`, report the conflict, and skip
  the push.

Push the branch with `--force-with-lease` when it has an open PR and gained a
commit or a rebase.

Reconcile is done when every dangling change sits in one bucket with its action
taken, and `git status` shows only unclaimed changes.

## 5. Record

Carry into the summary's **Reconciled** section one line per group: the paths,
the bucket, the action, and the evidence. Discarded work leaves no other trace,
so this record is the only way the user can see what went and why.
