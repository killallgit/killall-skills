---
name: session-eject
description: Save all work before usage runs out — commit, push, update or open draft PRs, and stop. `now` skips waiting for subagents.
disable-model-invocation: true
---

# Session eject

Usage is about to run out. Get every change this session made onto a remote
branch with a PR, then stop. Budget is the constraint: no new work, no
refactors, no fixes beyond what a commit needs. When a `caveman` skill is
available in this session, invoke it first.

Mode comes from the argument:

- none or `soft`: wind down. Subagents finish and report first.
- `now`: eject immediately. Skip step 1.

## 1. Wind down subagents (soft only)

Send each running subagent and teammate one message: stop starting new work,
commit what it has in its worktree, and report in three lines what is done and
what is left. Wait for every one to report or exit. Start nothing new while
waiting. This step is done when no subagent is still running.

## 2. Find the work

List every worktree and repository this session changed, including subagent
worktrees. For each, note the branch, uncommitted changes, unpushed commits,
and the open PR, if any (`gh pr view --json number,url,state`).

When a change sits on the default branch, move it to a new branch
`eject/<short-slug>` before committing. The eject never pushes to the default
branch.

## 3. Commit and push

In each worktree from step 2:

1. `git add -A`. Before committing, read `git diff --cached --stat`. Unstage any
   file that holds secrets or is a large build artifact.
2. Commit with the repository's message convention, marked as work in progress,
   for example `wip: <what the change does>`. When a hook fails, commit with
   `--no-verify` and record that in the PR body. Saving the work comes before
   the gate.
3. Push with `-u`. Use `--force-with-lease` only when the branch was rebased.

## 4. Update or open the PR

- **Open PR exists**: add a comment saying the session was ejected, what landed,
  and what is left. In soft mode, use the subagent reports from step 1.
- **No PR**: `gh pr create --draft --title "[ejected session]: <short desc>"`.
  The body lists what is done, what is left, and any `--no-verify` commit.

In `now` mode, keep the body to what you already know. Do not investigate.

## 5. Hand off and stop

Report one line per branch: branch, PR URL, and state (updated or new draft).
Name any subagent still running in `now` mode.

End with a **handoff**: one paragraph, printed last, that the user pastes into
a fresh agent to resume. That agent has none of this session's context, so the
paragraph stands alone in plain prose. It names the repository path, each
branch and PR URL, the goal of the work, what is done, what is left, the next
concrete step, and any trap waiting (a `--no-verify` commit, a subagent that
never reported, a failing test). Keep it under 120 words. Print it as plain
text with no heading or code fence, so it copies cleanly.

Then stop. Take no further action this session.
