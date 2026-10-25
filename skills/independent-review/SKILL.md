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

- **Open, not draft**: use it. Push any unpushed commits.
- **Open, draft**: `gh pr ready`, and say so in the report. CodeRabbit skips
  drafts.
- **None, or merged or closed**: push the branch with `-u` and `gh pr create`
  with a title and body in the repository's convention. A merged branch has
  nothing new to review; stop and tell the user.
- **On the default branch**: stop and tell the user. There is nothing to review
  until the work sits on its own branch.

This step is done when the pushed `HEAD` has an open, non-draft PR.

## 2. CodeRabbit

Run `scripts/wait-for-action.sh --coderabbit` from the `wait-for-action` skill.
It blocks until CodeRabbit finishes reviewing `HEAD`.

| Result | Next |
|---|---|
| `DONE`, not `rate limited` or `skipped` | Step 3 |
| `DONE` with `rate limited` or `skipped` | Step 4: no review was posted |
| `ERROR`: no status after a minute | Step 4 |
| `TIMEOUT` | Run again with `--ttl 30m`. Still pending: step 4 |
| `FAILED` | Step 4 |

## 3. Resolve CodeRabbit's findings

Read the inline comments and the review bodies with the `gh api` commands in
the `wait-for-action` skill. Rule only on findings from the newest review:
skip comments that are replies and threads you already answered. Rule on every
finding, inline and in the body: **fix** or **decline** with a one-line reason.

Fix in commits and push. Answer each inline comment on its thread:

```bash
gh api -X POST 'repos/{owner}/{repo}/pulls/<n>/comments/<id>/replies' -f body='<commit or reason>'
```

Answer a review-body finding in one `gh pr comment`. After a push, run step 2
again.

Done when every finding is fixed in a pushed commit or declined with its reason
in a reply. Stop after three rounds and report what is still open.

## 4. Fresh local review

Dispatch one reviewer that starts with **fresh context**: a new subagent, never
a fork, and never this session. Where the host has no subagents, a headless
`claude -p` or `codex exec` process serves. Pick the best fit installed: a
`reviewer` agent, else a general-purpose subagent.

The brief names the base branch, tells the reviewer to diff `base...HEAD`, and
asks for a review only: no edits, no commits, no PR comments. Leave out the PR
number, the author's reasoning, the task history, and any verdict on the code;
the PR body is the author's conclusion, and a reviewer handed it confirms it.
It returns findings as `file:line`, severity, and the failure scenario, ranked
most-severe first, or states that it found none.

Rule on each finding as in step 3, then push. Local findings have no thread, so
the report in step 5 is their record. Each further round dispatches a new
reviewer.

Done when a round returns no finding to fix. Stop after two rounds and report
what is still open.

## 5. Report

End with a summary the user reads in seconds. Lead with the PR URL and who
reviewed (CodeRabbit, the local agent, or both). Then one bullet per finding,
one or two sentences each: what the reviewer found, and what happened to it
(fixed, declined with the reason, or still open). Group bullets by reviewer when
both ran. Cut praise, process narration, and anything that is not a finding.
Leave the PR open; merging is the user's call.
