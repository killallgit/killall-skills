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
runs a local review agent, so the review never waits on a bot.

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

| Reviewer | The repo runs it when | Wait |
|---|---|---|
| CodeRabbit | `.coderabbit.yaml` exists | `scripts/wait-for-action.sh --coderabbit --ttl 10m` |
| PR-Agent | `.pr_agent.toml` exists, or a workflow under `.github/workflows` uses `pr-agent` | `scripts/wait-for-action.sh --pr-agent --ttl 5m` |

The script is in the `wait-for-action` skill. Run each wait with
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
reviewer that gave nothing and why. Then one bullet per finding, one or two
sentences each: what the reviewer found, and what happened to it (fixed,
declined with the reason, or still open). Group bullets by reviewer when
several ran. Cut praise, process narration, and anything that is not a finding.
Leave the PR open; merging is the user's call.
