---
name: git-janitor
description: >
  Clean up local Git when the user says "clean up our local git", prune the
  repo, or review stale branches and worktrees. Inspect uncommitted and
  unpublished work in every worktree first, discard work that is superseded
  or over 60 days old when justified, then remove merged and stale local
  worktrees and branches. Record what was discarded and why.
---

# Git janitor

`/git-janitor` runs full local cleanup in the current repository. Command
arguments can name another repository or narrow the request to an audit. The
same workflow applies when the user asks in plain language or delegates to
the `git-janitor` agent. "Clean up local git" authorizes the local cleanup
policy below. The invoking agent owns cleanup decisions and checks any
read-only findings from `git-janitor-investigator`. Follow any more specific
instruction in the user's request.

## 1. Set the scope

Confirm the repository root and resolve the default branch to a local commit.
Use a default named by the user; otherwise try `origin/HEAD`, then
`gh repo view --json defaultBranchRef` if available. Use `main` or `master`
only when one is the sole plausible local default. Ask only if the reference
remains ambiguous. Record the current checkout, all local branch tip OIDs,
and `git worktree list --porcelain`.

Cleanup is local: never push, delete remote branches, or rewrite remote refs.
Keep the default branch and the checkout running this task. Their disposable
working changes may still be cleaned path by path after inspection.

## 2. Inspect work at risk first

Visit **every** worktree before removing any of them, including the current
checkout and detached worktrees. Record its HEAD, branch, lock state,
`git status --porcelain --untracked-files=all`, staged and unstaged diffs,
untracked paths, and any ignored files that a removal would erase. Inspect
enough of the content to understand the work. Record the newest relevant
file modification time when available; a worktree with recent edits needs
judgment even when its branch tip is old.

For each branch, separately count commits not reachable from the default and
commits ahead of its configured upstream. If no upstream exists, say
"unpublished status unknown" and inspect the branch history rather than
assuming zero unpushed commits. A local remote-tracking ref may be stale; do
not claim it proves the live remote state. Show the branch's last commit date,
ahead/behind counts, and the commit subjects or files that explain its work.

Compare dirty files and branch commits with the current default and other
retained work. `git cherry`, a tree comparison, and file content can show
that a patch or result already landed through a squash, cherry-pick, or later
implementation. A three-dot diff lists files touched since divergence, not
necessarily content still absent from default. Being behind default alone
does not make changes disposable. Classify local work as **landed or clearly
superseded**, **disposable after inspecting its purpose**, or **valuable /
uncertain**; note the evidence for each classification.

Delegate read-only investigation of unmerged branches to
`git-janitor-investigator` in bounded parallel calls when available. Give it
the expected tip OID, default ref, upstream, and linked worktree path. If it
is unavailable, inspect those signals inline and query PRs with
`gh pr list --state all --head "$short_branch"`. A failed PR lookup is
unknown, not no PR. Recheck pivotal agent findings yourself.

## 3. Decide and clean without repeated prompts

- **Merged:** Once its worktree data has been assessed, remove a clean linked
  worktree and delete its merged local branch automatically. If the worktree
  is dirty, discard it automatically when its local changes are landed,
  superseded, or clearly disposable. Otherwise keep it and explain why.
- **Older than 60 days:** A local branch whose latest commit is older than
  60 days may be force deleted even with unpublished or unmerged commits.
  Remove its linked worktree first. For a dirty worktree, judge its actual
  files case by case, including recent edits; do not use the old branch tip
  alone to discard recent or unclear working data. Record any open PR or
  unpublished commits in the removal note.
- **Younger than 60 days:** Discard a local branch or dirty worktree without
  asking when its work is landed, clearly superseded, or clearly disposable
  after inspection. Preserve valuable or uncertain work and say what needs
  a human decision.
- **Detached, locked, or missing:** Inspect detached commits and working
  changes under the same rules. Preserve a locked worktree or one whose
  contents cannot be inspected; report the obstacle instead of escalating
  force.

The age rule is permission, not a substitute for understanding dirty data.
The user's standing cleanup request authorizes these local actions. Do not
stop after the inventory to ask for each branch or worktree.

## 4. Apply and leave a receipt

Before each discard, record the path, branch, tip OID, unpublished commit
count, dirty paths, and the evidence that the work can go. Recheck the tip,
status, worktree mapping, and relevant content immediately before acting.
If anything changed, skip that item and report it.

Use `git worktree remove "$path"` for clean linked worktrees and
`git worktree remove --force "$path"` for dirty ones classified disposable.
Never force-remove the running checkout or a locked worktree. For disposable
changes in the running checkout, use targeted restore/clean operations on
the reviewed paths instead of a blanket reset or clean. Delete merged
branches with `git branch -d -- "$branch"`; use
`git branch -D -- "$branch"` for authorized old or superseded unmerged
branches after their worktrees are gone. A failed command is a skipped item,
not a reason to silently widen the force.

Run `git worktree prune --dry-run -v`, then prune stale metadata that is
clearly abandoned; preserve entries that may represent temporarily missing
worktrees. Report dirty and unpublished work first: what was discarded,
what was kept, and the evidence. Then list worktrees, branches, and stale
metadata removed, with exact names and paths. State any remaining decisions
or failures plainly.
