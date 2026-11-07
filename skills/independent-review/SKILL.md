---
name: independent-review
description: Get the current branch reviewed by a reviewer that did not write it. Opens a PR if none exists, waits for the repo's CI reviewers (CodeRabbit, PR-Agent) when it has any, otherwise runs a fresh-context local review agent, then resolves the findings. Use when the user asks for an independent review, or when another skill calls for one.
---

# Independent review

The author cannot review its own work: it carries the reasoning that produced
the code, so it reads intent where a stranger reads the diff. Put the branch in
front of a reviewer with no part in writing it, then resolve what it finds. When
a `caveman` skill is available in this session, invoke it first.

An agent may run this skill itself, including from another skill such as
`lets-finish`. A CI reviewer is optional and never worth a long wait:
when the repo has none, or it is rate limited, skipped, slow or broken, step 4
tries a local review agent rather than waiting longer on a bot. If no
independent route works, review is BLOCKED and the calling workflow stops.

A failed reviewer invocation is **not a completed review**. Authentication,
quota, provider, tool or process failures trigger another available independent
route, not a downgrade to the author's manual review or passing tests. Those
checks are useful, but neither substitutes for independent review. This rule
also binds callers such as `lets-finish` and repository shipping workflows.
An explicit user instruction such as `don't review` is a waiver. A caller's
docs-only exemption may skip invoking this skill, but is not a waiver once
independent review has been requested or attempted.

## 1. Get a PR

Run `gh pr view --json number,url,state,isDraft,headRefName`.

- **Open, not draft**: use it. Push any unpushed commits.
- **Open, draft**: `gh pr ready`, and say so in the report. CI reviewers skip
  drafts.
- **None, or merged or closed**: push the branch with `-u` and `gh pr create`
  with a title and body in the repository's convention. A merged branch has
  nothing new to review; stop and tell the user.
- **On the default branch**: stop and tell the user. There is nothing to review
  until the work sits on its own branch.

This step is done when the pushed `HEAD` has an open, non-draft PR.

## 2. CI reviewers

Find which reviewers this repo runs. Start every one that applies; the waits are
independent.

Read `references/cr-requirements.md` before deciding on CodeRabbit, and decide by
its checks. A repo instruction that calls for CodeRabbit on some changes, such as
substantial ones, counts as being asked: do not skip it for want of a request in
the user's message.

| Reviewer | The repo runs it when | Wait |
|---|---|---|
| CodeRabbit | The user or the repo's instructions call for it, and its [requirements](./references/cr-requirements.md) are met | `scripts/wait-for-action.sh --coderabbit --ttl 10m` |
| PR-Agent | `.pr_agent.toml` exists, or a workflow under `.github/workflows` uses `pr-agent` | `scripts/wait-for-action.sh --pr-agent --ttl 5m` |

The script is in the `wait-for-action` skill. These waits cover the review
only: CI is the caller's step (`--checks`, as `lets-finish` runs it). `--ready`
is not used here because it waits for CodeRabbit whenever the repo runs it,
and this skill runs CodeRabbit only when it is called for. In a checkout where
`git rev-parse HEAD` fails, add `--pr <n>` to a wait: it reads the PR's head
commit.

Run each wait with
`run_in_background` and continue when its completion notice arrives: Claude
Code ends a foreground Bash call at 2 minutes by default and 10 at most, which
cuts a review wait short and looks like a hang.

Neither row applies: go to step 4, and say in the report that no CI reviewer was
found. A reviewer installed without its config file is not detected.

The `--ttl` values are the budget. Do not extend them or rerun a wait that
ended short.

| Result | Next |
|---|---|
| `DONE` (exit 0) | Step 3 for that reviewer |
| `NOT_REVIEWED` (4), `TIMEOUT` (2), `FAILED` (1), `ERROR` (3) | That reviewer gave nothing. Note its line for the report |

When no reviewer reached `DONE`, go to step 4.

## 3. Resolve CI findings

Read the newest review of each reviewer that finished. Rule only on findings
from it: skip comments that are replies and threads you already answered. Rule
on every finding, inline and in the body: **fix** or **decline** with a
one-line reason.

- **CodeRabbit**: inline threads are listed in `findings.json`; findings outside
  the diff are in the newest review body. The `wait-for-action` skill has the
  `gh api` commands to read it, to resolve a thread and to answer one.
- **PR-Agent**: the whole review is in `review.md`. It has no threads.

Fix in commits and push. Answer each CodeRabbit thread on its thread and resolve
it once fixed. Answer everything else, including PR-Agent, in one
`gh pr comment`. After a push, run step 2 again for the reviewers that had
findings.

Done when every finding is fixed in a pushed commit or declined with its reason
in a reply. Stop after three rounds and report what is still open.

## 4. Fresh local review

Dispatch one reviewer that starts with **fresh context**: a new subagent, never
a fork, and never this session. Where the host has no subagents, a headless
`claude -p` or `codex exec` process serves. Pick the best fit installed: a
`reviewer` agent, else a general-purpose subagent.

If dispatch fails, or its response contains neither a findings list nor an
explicit statement that it found no issues (including empty or truncated
responses without either verdict):

1. Check the other installed review skills and supported agents/processes for
   an independent route that is actually available. A different skill using the
   same failing provider is not a fallback; do not repeat an unchanged auth or
   quota failure.
2. Attempt another available route with fresh context and the same neutral
   brief. Continue through viable alternatives until one returns a review or
   none remain. Never change credentials or install tooling without authority.
3. If none works, mark independent review **BLOCKED**, list the failed routes
   and concrete errors, and stop the calling workflow before merge, release or
   deployment. Ask the user to restore a review route or explicitly waive
   independent review. Routine permission to ship is not a review waiver.

A successful process exit, an attempted dispatch, or the author's own review
cannot satisfy this step; an independent reviewer must return findings or an
explicit no-findings verdict. A waiver permits proceeding but does not turn a
blocked review into a completed one.

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
reviewed (CodeRabbit, PR-Agent, the local agent, or a mix), and name any CI
reviewer that gave nothing and why. When CodeRabbit did not run, say which
check in `references/cr-requirements.md` ruled it out. Then one bullet per finding, one or two
sentences each: what the reviewer found, and what happened to it (fixed,
declined with the reason, or still open). Group bullets by reviewer when
several ran. Cut praise, process narration, and anything that is not a finding.
If blocked, lead with **Independent review BLOCKED**, the failed routes and
errors, and what the user must unblock or explicitly waive. If waived, label
it **WAIVED**, never reviewed or passed. Always distinguish an attempted
review from a completed independent verdict.

Leave the PR open; merging is the user's call.
