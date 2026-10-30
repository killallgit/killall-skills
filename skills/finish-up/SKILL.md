---
name: finish-up
description: Wrap up finished work. Confirm the PR's CI passed and any required review is done, merge it, update the tickets and beads it relates to, then offer to clean up the branch and worktree. Use when the user says "finish up", "wrap this up", or invokes `/finish-up`.
disable-model-invocation: true
---

# Finish up

Land the PR(s) for this work and close out their tickets. The user wants to read
the run like a script, so every step prints one line when it starts and one line
when it ends. When a `caveman` skill is available in this session, invoke it
first.

## Output

Show each step's pending line (`confirming ci...`) as the Bash call's
`description` while it runs. When it ends, print the result line. The result
lines stay in the transcript, so the finished run reads top to bottom:

```
[+] ci passed
[+] reviewed by coderabbit, <login>
[+] merged <PR title>
[+] found 2 beads
[+] updated <id>: <title>
[+] updated <id>: <title>
```

- `[+]` the step succeeded.
- `[-]` nothing to do (`[-] No related tickets found`).
- `[x]` the step failed. Print the reason, stop, and do not run later steps.

No other narration between lines.

## PRs

Use the PR numbers in the argument. With none, use the open PR for the current
branch (`gh pr view --json number,title,url,headRefName,reviewDecision,body`).
When the branch is the default branch, stop and say so. When the branch has no
open PR, run step 0 for it first. Run steps 1 to 4 for each PR in turn; steps 5
and 6 run once, over all of them.

## 0. opening PR... (only when the branch has no open PR)

1. Push the branch with `-u` and `gh pr create` with a title and body in the
   repository's convention. `[+] opened <PR title>`.
2. Wait for CI as in step 1. A failure is `[x]` and stops here.
3. Invoke the `independent-review` skill and let it finish. Where the host
   refuses to run it from another skill, follow its `SKILL.md` steps directly.
   `[+] independent review done` with its fixed and declined counts.

Its fixes are new pushes, so step 1 runs again afterwards.

## 1. confirming ci...

`gh pr checks <n> --watch --fail-fast`. Exit 0: `[+] ci passed`. Exit 1: `[x]`
with the failing check names and stop. A PR with no checks counts as passed;
say `[+] ci passed (no checks)`.

## 2. confirming review...

A review is needed when the repo has a `.coderabbit.yaml`, or `reviewDecision`
is `REVIEW_REQUIRED` or `CHANGES_REQUESTED`.

- **Not needed** and no review exists: `[-] no review needed`.
- **CodeRabbit**: run `wait-for-action --coderabbit` and read its exit code as
  the `wait-for-action` skill does. Anything but `DONE`, or any unresolved
  thread left, is `[x] review not done` with the reason; point the user to
  `/ship` or `/independent-review` to resolve it.
- **Human reviewers**: `reviewDecision` must be `APPROVED`, else `[x] awaiting
  approval`.

Name every reviewer that reviewed: `[+] reviewed by coderabbit, <login>`.

## 3. merging <PR title>...

`gh pr merge <n> --squash`. The branch is deleted in step 6, not here, because a
worktree holding it blocks the local delete. A `ship` merge guard may block the
command until CodeRabbit's check succeeds; that is an `[x]`, not something to
bypass. A conflict or branch-protection refusal is also `[x]` with gh's message.
Then `git fetch --prune`. `[+] merged <PR title>`.

## 4. finding tickets|beads...

Collect candidate ids from the branch name, PR title and body, and the PR's
commit messages. Look them up in each tracker that exists:

- **Beads**: only when `.beads/` exists and `bd` is installed. `bd search <id>`
  for each id found, and `bd search "<PR title>" --status open` for a match by
  title.
- **Jira**: ids shaped like `ABC-123`, through the Atlassian MCP tools when the
  host has them (`getJiraIssue`).
- **GitHub issues**: `gh pr view --json closingIssuesReferences`, plus `#n`
  references in the body.

Skip a tracker that is not there (no `.beads/`, no `bd`, no Jira tools, no
issue references) without comment. Drop anything already closed. If no tracker
is available, print `[-] No ticket tracker available`; if one is but nothing
matches, print `[-] No related tickets found`. Either way go straight to step 6.
Otherwise `[+] found N beads|issues`.

## 5. updating <id>: <one line title>...

Update every ticket automatically, one at a time, no confirmation:

- Closed by the PR (`closes`, `fixes`, `resolves`, or its id is the branch name):
  - beads: `bd close <id> --reason "Merged in <PR url>"`
  - Jira: add a comment with the PR url, then transition to Done
    (`getTransitionsForJiraIssue`, `transitionJiraIssue`)
  - GitHub: already closed by the merge; add nothing
- Only mentioned (`refs`, `part of`, a title match): add a comment with the PR
  url and leave the status.

`[+] updated <id>: <title>` and the new state. A failed update is `[x]` for that
ticket; carry on with the rest and list the failures at the end.

## 6. Clean up

Ask `Clean up branch <name> and its worktree? [y/n]` and wait for the answer.

- **n**: leave both. Stop.
- **y**: for each merged PR, from the main checkout (never from inside the
  worktree being removed):
  1. If the worktree has uncommitted changes, keep it and say so.
  2. Otherwise `git worktree remove <path>`, then `git branch -D <branch>`. The
     squash merge hides the commits from `git branch -d`, but the merge in step 3
     already proved them landed.
  3. `git push origin --delete <branch>` when the remote branch still exists.
  4. `git checkout <default> && git pull` in the main checkout.

  `[+] cleaned <branch>`.
