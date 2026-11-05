---
name: wait-for-action
description: Wait for CI, PR checks, a review, or a workflow run in one blocking call. Use before a merge ("is it ready to merge", wait for the PR to be green, CI, then the CodeRabbit or PR-Agent review), after a push, merge or workflow dispatch, or when a run failed and you need its log. Replaces any hand-written `gh run watch`, `gh pr checks --watch` or sleep loop.
---

# wait-for-action

One blocking Bash call that polls until a workflow run, every check on a pull
request, or the CodeRabbit or PR-Agent review reaches a terminal state. Costs no
conversation tokens while the wait is in flight, and pulls logs to disk instead
of into context.

## When to use

- A pull request has to be ready to merge: CI green and, where the repo runs
  one, the review done. That wait is `--ready`
- CI on a pull request has to finish before the next step. That wait is
  `--checks`, which covers every check on the head
- Only the CodeRabbit or PR-Agent review matters: `--coderabbit` or `--pr-agent`
- A workflow was just triggered (push, `gh workflow run`, `gh pr merge`) and the
  next step depends on its result
- A run is already going and the user wants to know when it lands
- A run failed and you need the failing output

Do **not** poll in the conversation. Every turn replays the full context — hand
the wait to the script.

## How

```bash
./scripts/wait-for-action.sh --ready [--pr N] [--repo OWNER/REPO] [--ttl 15m]
./scripts/wait-for-action.sh --checks [--pr N] [--repo OWNER/REPO] [--ttl 15m]
./scripts/wait-for-action.sh --run-id <id> [--repo OWNER/REPO] [--ttl 15m]
```

`--ready` waits for CI, then the review. `--checks` waits for the whole PR
rollup. With no `--run-id`, `--checks` or `--ready`, the script resolves the
newest Actions run for the current `HEAD` commit. That is one workflow, right
after a push, and wrong after any later commit — pass the id when you have it.
Confirming CI uses `--checks`; confirming a merge is safe uses `--ready`.

| Flag | Default | Notes |
|---|---|---|
| `--ready` | off | `--checks`, then the review the repo runs; see below |
| `--checks` | off | every check on the PR head; see below |
| `--pr N` | open PR for the current branch | with `--checks`, `--ready`, `--coderabbit`, `--pr-agent`; the review waits read the PR's head commit from it |
| `--sha COMMIT` | `git rev-parse HEAD` | the commit for `--coderabbit`, `--pr-agent`, `--ready` and the no-flag run lookup; see below |
| `--run-id ID` | newest run for `HEAD` | |
| `--repo OWNER/REPO` | repo in cwd | with `--run-id`, `--checks` or `--ready` |
| `--ttl DURATION` | `15m` | `45s`, `15m`, `1h`; raise it for known-slow pipelines |
| `--tail N` | `40` | log lines echoed on failure |
| `--log-dir PATH` | `/tmp/actions/<run-id>` | `/tmp/actions/pr-<n>` with `--checks` and `--ready` |
| `--no-fail-fast` | off | wait for the whole run instead of bailing on the first failed job |
| `--quiet` | off | only the terminal line and any failure log |
| `--coderabbit` | off | wait for the CodeRabbit review of `HEAD` instead; see below |
| `--pr-agent` | off | wait for the PR-Agent review of `HEAD` instead; see below |
| `--no-trigger` | off | with `--coderabbit`, `--pr-agent` or `--ready`: report instead of commenting |

Getting a run id: `gh run list --limit 5 --json databaseId,workflowName,status`,
or `--json databaseId --jq '.[0].databaseId'` right after triggering.

### Poll schedule

Dense while failures are likely, sparse once the run is doing real work:

| Elapsed | Interval |
|---|---|
| 0–90s | 15s |
| 90s–3.5m | 30s |
| 3.5m–5.5m | 60s |
| 5.5m+ | 3m |

Setup failures — bad checkout, missing secret, broken install — surface in the
first window. A run still green at 5.5 minutes is working, and there is nothing
to learn by asking every few seconds.

### Exit codes

| Exit | Meaning |
|---|---|
| 0 | Run completed `success` (or `skipped`/`neutral`) |
| 1 | Run failed, or a job failed and fail-fast tripped |
| 2 | TTL expired — the run is still going |
| 3 | Usage error, or the API kept refusing |
| 5 | `--checks` and `--ready` only: no check ever appeared |

Exit 2 is not a failure of the run. Either invoke again with the same
`--run-id` (or the same `--checks --pr`) to keep waiting, or report that it
is still in flight.

### A checkout where `git rev-parse HEAD` fails

A worktree of a submodule with `core.worktree` set has no usable `git` in its
directory. The commit-based waits then need the commit named:

- `--pr N` reads the PR's head (`gh pr view --json headRefOid`), so
  `--ready --pr N`, `--coderabbit --pr N` and `--pr-agent --pr N` need no `git`
- `--sha COMMIT` names it directly, and also feeds the no-flag run lookup

`--checks --pr N` never needed `git`. `--checks` and `--ready` without `--pr`
find the PR from the current branch, which does need it: pass `--pr`.

## PR checks (`--checks`)

`gh run view` sees one Actions run. A pull request's CI is the rollup `gh pr
checks` reads: every Actions workflow, every other check run, and legacy
commit statuses. `--checks` polls that.

```bash
./scripts/wait-for-action.sh --checks --pr <n>
```

Checks register a few seconds after a push. An empty rollup is retried for 2
minutes, or until `--ttl` when that is shorter. Still empty: the line is
`NONE` and the exit is 5. That is "nothing started", including a path-filtered
workflow that never created a check.

A green result waits until the set of check names has stayed the same for 10
seconds, so a check that shows up late is included. A failure returns
immediately. `--no-fail-fast` waits until nothing is still pending, then fails
if any check failed.

The script classifies from the check's `state`. `gh pr checks` leaves
`STARTUP_FAILURE` and `STALE` in its pending bucket and treats `CANCELLED` as
neither a pass nor a fail, so those would hang a `--watch` or look like a pass.

| Result | States |
|---|---|
| pass | `SUCCESS` |
| skipping, counts as passed | `SKIPPED`, `NEUTRAL` |
| fail | `FAILURE`, `ERROR`, `TIMED_OUT`, `ACTION_REQUIRED`, `STARTUP_FAILURE`, `STALE`, `CANCELLED` |
| pending | `QUEUED`, `IN_PROGRESS`, `WAITING`, `PENDING`, `REQUESTED`, `EXPECTED`, and anything still running |

A state the table does not name, that already has a completion time, counts as
failed.

| Exit | Meaning |
|---|---|
| 0 | `DONE`: every check passed or skipped |
| 1 | `FAILED`: a check failed or was cancelled. Each name, state, and link is printed. An Actions job link also pulls that job's log |
| 2 | `TIMEOUT`: at least one check is still pending |
| 3 | `ERROR`: usage, or the API kept refusing |
| 5 | `NONE`: no check appeared |

Files for this mode land in `/tmp/actions/pr-<n>/`: `checks.json`, `summary.json`, `poll.log`, and `failed.log` when an Actions job failed.

## Ready to merge (`--ready`)

```bash
./scripts/wait-for-action.sh --ready --pr <n> [--ttl 15m] [--no-trigger]
```

Two waits, one answer. First everything `--checks` does. When every check
passed and the rollup shows a `CodeRabbit` check, or a check or workflow whose
name contains `pr-agent`, the script then waits for that review of the PR head,
with everything `--coderabbit` or `--pr-agent` does: the same triggers,
rate-limit handling and `--no-trigger`. CodeRabbit wins when the repo runs both;
run `--pr-agent` afterwards for the other. A repo with neither reviewer gets
`--checks` and its `DONE pass` line.

One `--ttl` covers both waits: the review gets what CI left. The first failure
returns at once. Only the review's `DONE` line is printed as terminal, and only
after CI passed, so one line and one exit code mean ready to merge. The CI hand-over
line starts with `CI passed`, which the Monitor pattern below ignores. Unresolved
CodeRabbit threads are listed after the `DONE` line as with `--coderabbit`.

| Exit | Meaning |
|---|---|
| 0 | CI green and the review done (or no reviewer, and CI green) |
| 1 | a check failed or was cancelled, or the review check failed. The line names which |
| 2 | `TIMEOUT`: a check, or the review, is still pending when `--ttl` ends |
| 3 | `ERROR`: usage, the API kept refusing, no open PR, or findings unreadable |
| 4 | `NOT_REVIEWED`: CodeRabbit is still rate limited or skipped after a trigger, or its reset is later than `--ttl` |
| 5 | `NONE`: no check appeared |

Files land in `/tmp/actions/pr-<n>/`, and the review's in `review/` below it
(`findings.json` or `review.md`, `poll.log`).

## Logs

Everything lands under `/tmp/actions/<run-id>/`:

| File | Contents |
|---|---|
| `run.json` | latest run + jobs + steps snapshot |
| `poll.log` | every line the script emitted, including those suppressed by `--quiet` |
| `jobs/<job>.log` | full log per job, fetched as each job completes |
| `failed.log` | raw log of the failing job (on exit 1) |

On failure the script already prints the `##[error]` lines and the last `--tail`
lines of the failing job. **That is normally enough — start from it.** If you
need more, `grep` the files; never `cat` a job log. They run to tens of
thousands of lines and will bury the context.

```bash
grep -n -i -m20 -E 'error|failed|exception' /tmp/actions/<run-id>/jobs/<job>.log
sed -n '1200,1260p' /tmp/actions/<run-id>/jobs/<job>.log   # around a hit
```

## CodeRabbit

CodeRabbit reviews in GitHub as an App, not an Actions run, so `gh run view`
cannot see it. It reports through a `CodeRabbit` check run on the commit
(older installs: a commit status; both are read). `--coderabbit` watches the
review of `HEAD` on the same poll schedule:

```bash
./scripts/wait-for-action.sh --coderabbit [--ttl 15m] [--no-trigger]
```

Push first: the review is for the pushed `HEAD` commit. The review is not
always automatic, so the script handles the states a plain poll cannot:

| State | What the script does |
|---|---|
| in progress | keeps polling |
| rate limited | reads the reset time from CodeRabbit's notice, sleeps until then if it fits in `--ttl`, then comments `@coderabbitai review` |
| skipped (label, draft, paused) | comments `@coderabbitai review` once; a label is never needed |
| no check after 3 minutes on an open PR | comments `@coderabbitai review` once |
| completed | reports `DONE`, the other checks' CI totals, and the unresolved CodeRabbit threads |

It never posts the same trigger twice: a review comment already newer than the
last check counts. `--no-trigger` reports instead of commenting.

| Exit | Meaning |
|---|---|
| 0 | `DONE`: reviewed. Findings are listed after the line and kept in `findings.json` |
| 1 | `FAILED`: the check failed |
| 2 | `TIMEOUT`: still pending |
| 3 | `ERROR`: no open PR for `HEAD`, the API kept failing, or the review finished but its inline findings could not be read |
| 4 | `NOT_REVIEWED`: still rate limited or skipped after a trigger, or the reset is later than `--ttl`; the line says how long |

On exit 4 report it to the user. If the line gives a reset time, rerun with a
`--ttl` that covers it.

Each finding carries its thread `id`. Resolve a thread once its finding is fixed,
so the next round lists only what is left:

```bash
gh api graphql -f query='mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}' -F id=<id>
```

Answer a thread with a reply:

```bash
gh api -X POST 'repos/{owner}/{repo}/pulls/<n>/comments/<id>/replies' -f body='<commit or reason>'
```

Unresolved threads are only what CodeRabbit left inline. Findings outside the
diff land in the review body, so read the newest one too (older bodies hold
findings from earlier rounds):

```bash
gh api --paginate 'repos/{owner}/{repo}/pulls/<n>/reviews?per_page=100' --jq '[.[] | select(.user.login=="coderabbitai[bot]" and .body!="")] | last | {submitted_at, body}'
```

## PR-Agent

[PR-Agent](https://github.com/qodo-ai/pr-agent) runs as a GitHub Action or App
and answers with one comment, not a check run, and its workflow run belongs to
the default branch's commit. `gh run view` and the CodeRabbit check cannot see
it. `--pr-agent` instead looks for its comment (a bot comment carrying
`<!-- pr-agent:review`) last updated after the `HEAD` commit was made, and
comments `/review` once when there is none:

```bash
./scripts/wait-for-action.sh --pr-agent [--ttl 5m] [--no-trigger]
```

Push first. A review takes about a minute; the default `--ttl` is generous. The
`/review` workflow only runs for repo members and owners.

| Exit | Meaning |
|---|---|
| 0 | `DONE`: reviewed. The comment is kept in `review.md` |
| 2 | `TIMEOUT`: no review of `HEAD` yet. Check the repo's workflow run for the `/review` comment |
| 3 | `ERROR`: no open PR for `HEAD`, or the API kept failing |

PR-Agent has no threads to resolve. Answer its findings in one `gh pr comment`.

## Fail-fast

By default the script exits as soon as any job concludes failure, without
waiting for the rest of the run — the outcome is already decided and the failing
job's log is already on disk. `--checks` does the same on the first failed or
cancelled check. If the workflow has jobs marked `continue-on-error` whose
failure is expected, pass `--no-fail-fast`.

## Foreground vs background

Foreground is the default for a workflow run: one call, blocks, returns the
answer. A foreground Bash call in Claude Code ends at 2 minutes by default and
10 at most, so a wait that can run longer (any `--ready` or `--coderabbit` wait, a long
`--ttl`) goes in the background: `run_in_background`, then continue when the
completion notice arrives.

Run it in the background too when the user wants you to keep working
meanwhile, and watch for the terminal line:

```
Monitor pattern: ^\[t=\d+s\] (DONE|FAILED|TIMEOUT|ERROR|NOT_REVIEWED|NONE)
```

## Notes

- Requires `gh` (authenticated) and `jq`. `--ready`, `--coderabbit` and `--pr-agent` also need `uv` or `python3`.
- A run created seconds ago can 404 until GitHub catches up; the script retries
  through that for the first minute before giving up with exit 3.
- Each poll is one API call, plus one per job at the moment it completes.
