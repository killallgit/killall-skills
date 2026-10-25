---
name: independent-review
description: Get the current branch reviewed by a reviewer that did not write it. Opens a PR if none exists, runs CodeRabbit when available, otherwise a fresh-context local review agent, then resolves the findings.
disable-model-invocation: true
---

# Independent review

The author cannot review its own work: it carries the reasoning that produced
the code, so it reads intent where a stranger reads the diff. Put the branch in
front of a reviewer with no part in writing it, then resolve what it finds. When
a `caveman` skill is available in this session, invoke it first.

## 1. Get a PR

Run `gh pr view --json number,url,state,isDraft,headRefName`.

- **Open PR**: use it. Push any unpushed commits.
- **None**: push the branch with `-u` and `gh pr create` with a title and body
  in the repository's convention. On the default branch, stop and tell the
  user: there is nothing to review until the work sits on its own branch.
- **Draft**: mark it ready with `gh pr ready`. CodeRabbit skips drafts.

This step is done when the pushed `HEAD` has an open, non-draft PR.

## 2. CodeRabbit

Run `wait-for-action --coderabbit`. It blocks until CodeRabbit finishes
reviewing `HEAD`.

| Result | Next |
|---|---|
| `DONE` with `Review completed` | Step 3 with the CodeRabbit comments |
| `DONE` with `rate limited` or `skipped` | Step 4: no review was posted |
| `ERROR` (CodeRabbit not installed or no status) | Step 4 |
| `TIMEOUT` | Report that CodeRabbit is still pending. Step 4 runs meanwhile; step 3 takes CodeRabbit's comments once they land |
| `FAILED` | Step 4 |

## 3. Resolve CodeRabbit's findings

Read the inline comments and the review bodies with the `gh api` commands in
the `wait-for-action` skill. Rule on every finding in both: **fix** or
**decline** with a one-line reason. Fix in
commits, push, and reply on each thread with the commit or the reason. When a
fix pushes new commits, run `wait-for-action --coderabbit` again.

Done when every finding is fixed in a pushed commit or declined with a reason
on its thread or, for a review-body finding, in a PR comment. Stop after three rounds and report what is still open.

## 4. Fresh local review

Dispatch one reviewer that starts with **fresh context**: a new subagent, never
a fork, and never this session. Where the host has no subagents, a headless
`claude -p` or `codex exec` process serves. Pick the best fit installed: a
`reviewer` agent, else the `code-review` skill run inside a general-purpose
subagent, else a general-purpose subagent with the brief below.

The brief names the PR number and its base branch, and asks for a review
only. Leave out the author's reasoning, the task history, and any verdict on
the code; a reviewer handed the author's conclusion confirms it. It returns
findings as `file:line`, severity, and the failure scenario, ranked
most-severe first, or states that it found none.

Rule on each finding as in step 3, then push. Each further round dispatches a
new reviewer. Done when a round returns no finding to fix. Stop after two
rounds and report what is still open.

## 5. Report

End with a summary the user reads in seconds. Lead with the PR URL and who
reviewed (CodeRabbit, the local agent, or both). Then one bullet per finding,
one or two sentences each: what the reviewer found, and what happened to it
(fixed, declined with the reason, or still open). Group bullets by reviewer when
both ran. Cut praise, process narration, and anything that is not a finding.
Leave the PR open; merging is the user's call.
