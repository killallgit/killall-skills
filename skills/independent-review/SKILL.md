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

Run the `wait-for-action` skill's script once:

```bash
python3 scripts/wait_for_action.py --pr <n> --ttl 10m
```

It discovers CI and bot activity together, without triggering reviews. Use a
background call when the host's foreground timeout is shorter than the budget.
Do not extend or repeat the wait to chase an absent, skipped, or rate-limited bot.
Read `references/cr-requirements.md` when evaluating whether CodeRabbit is needed;
discovery alone never makes any reviewer required.

Read the saved `activity.json`. A current-head submitted review or a review
comment explicitly tied to that head can supply the independent verdict.
Inspect its body: a bot acknowledgement, rate-limit notice, successful check,
or the monitor's `DONE` line is not a review verdict. The monitor can fail on CI
while a usable review exists, so inspect the evidence rather than equating its
exit code with review completion. CI failures remain the caller's merge gate.

If an independent verdict exists, continue to step 3. Otherwise, report the
missing or unconfirmed review and use step 4. If the user or project explicitly
requires a particular reviewer, an unavailable one is **BLOCKED** unless that
requirement is waived; do not silently substitute a different reviewer.

## 3. Resolve CI findings

Read the newest review of each reviewer that finished. Rule only on findings
from it: skip comments that are replies and threads you already answered. Rule
on every finding, inline and in the body: **fix** or **decline** with a
one-line reason.

- **Submitted reviews:** read `repos/{owner}/{repo}/pulls/<n>/reviews` with
  `gh api --paginate`; use the newest actual review for the current head.
- **Inline findings:** read `repos/{owner}/{repo}/pulls/<n>/comments`, and use
  GraphQL `reviewThreads` to identify unresolved threads. Reply through
  `pulls/<n>/comments/<id>/replies`, then resolve with `resolveReviewThread`.
- **Comment-based reviews:** read the bot's review body from `activity.json` or
  `repos/{owner}/{repo}/issues/<n>/comments`. Without reliable head attribution,
  do not count a comment as the current review.

Fix in commits and push. Answer each CodeRabbit thread on its thread and resolve
it once fixed. Answer everything else, including PR-Agent, in one
`gh pr comment`. After a push, run step 2 again for the reviewers that had
findings.

Done when every finding is fixed in a pushed commit or declined with its reason
in a reply. Stop after three rounds and report what is still open.

## 4. Fresh local review

Dispatch one reviewer that starts with **fresh context**: a new subagent, never
a fork, and never this session. Where the host has no subagents, a headless
`claude -p` or `codex exec` process serves.

Use the user's previously stated reviewer choice for this project when it is
available; check project instructions and relevant saved project preferences.
Otherwise, pick an available agent explicitly defined for code review. If no
such agent is available and no available project choice exists (including when
a previously stated choice is unavailable), ask the user which agent or process
to use and wait for their answer before dispatching. Do not
silently default to a general-purpose subagent or headless process. If no user
can answer (for example, in a noninteractive workflow), mark independent review
**BLOCKED** and stop the calling workflow. A previous choice applies only to
its stated project and scope, not every project.

The brief names the base branch, tells the reviewer to diff `base...HEAD`, and
asks for a review only: no edits, no commits, no PR comments. Leave out the PR
number, the author's reasoning, the task history, and any verdict on the code;
the PR body is the author's conclusion, and a reviewer handed it confirms it.
It returns findings as `file:line`, severity, and the failure scenario, ranked
most-severe first, or states that it found none.

If dispatch fails, or its response contains neither a findings list nor an
explicit statement that it found no issues (including empty or truncated
responses without either verdict):

1. Check the other installed review skills and supported agents/processes for
   an independent route that is actually available. A different skill using the
   same failing provider is not a fallback; do not repeat an unchanged auth or
   quota failure.
2. Apply the reviewer-selection rule above to each fallback: use an available
   previously stated project choice or an explicitly defined review agent;
   otherwise ask which agent or process to use and wait. Attempt the selected
   route with fresh context and the same neutral brief. Continue through viable
   alternatives until one returns a review or none remain. Never change
   credentials or install tooling without authority.
3. If none works, mark independent review **BLOCKED**, list the failed routes
   and concrete errors, and stop the calling workflow before merge, release or
   deployment. Ask the user to restore a review route or explicitly waive
   independent review. Routine permission to ship is not a review waiver.

A successful process exit, an attempted dispatch, or the author's own review
cannot satisfy this step; an independent reviewer must return findings or an
explicit no-findings verdict. A waiver permits proceeding but does not turn a
blocked review into a completed one.

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
