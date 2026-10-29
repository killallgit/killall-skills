---
name: wait-for-action
description: Wait for a GitHub Actions run to finish, or for the CodeRabbit review of HEAD with --coderabbit. Use when a workflow has been triggered and later work depends on it passing, when you need to know why a run failed, or when the user says to wait for CodeRabbit.
---

# wait-for-action

One blocking Bash call that polls a workflow run until it reaches a terminal
state. Costs no conversation tokens while the run is in flight, and pulls logs
to disk instead of into context.

## When to use

- A workflow was just triggered (push, `gh workflow run`, `gh pr merge`) and the
  next step depends on its result
- A run is already going and the user wants to know when it lands
- A run failed and you need the failing output

Do **not** poll in the conversation. Every turn replays the full context — hand
the wait to the script.

## How

```bash
./scripts/wait-for-action.sh --run-id <id> [--repo OWNER/REPO] [--ttl 15m]
```

With no `--run-id`, it resolves the newest run for the current `HEAD` commit.
That is right after a push and wrong after any later commit — pass the id when
you have it.

| Flag | Default | Notes |
|---|---|---|
| `--run-id ID` | newest run for `HEAD` | |
| `--repo OWNER/REPO` | repo in cwd | requires `--run-id` |
| `--ttl DURATION` | `15m` | `45s`, `15m`, `1h`; raise it for known-slow pipelines |
| `--tail N` | `40` | log lines echoed on failure |
| `--log-dir PATH` | `/tmp/actions/<run-id>` | |
| `--no-fail-fast` | off | wait for the whole run instead of bailing on the first failed job |
| `--quiet` | off | only the terminal line and any failure log |
| `--coderabbit` | off | wait for the CodeRabbit review of `HEAD` instead; see below |

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

Exit 2 is not a failure. Either invoke again with the same `--run-id` to keep
waiting, or report that the run is still in flight — do not call it broken.

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

Unresolved threads are only what CodeRabbit left inline. Findings outside the
diff land in the review body, so read it too:

```bash
gh api --paginate 'repos/{owner}/{repo}/pulls/<n>/reviews' --jq '.[] | select(.user.login=="coderabbitai[bot]" and .body!="") | {submitted_at, body}'
```

## Fail-fast

By default the script exits as soon as any job concludes failure, without
waiting for the rest of the run — the outcome is already decided and the failing
job's log is already on disk. If the workflow has jobs marked
`continue-on-error` whose failure is expected, pass `--no-fail-fast`.

## Foreground vs background

Foreground is the default: one call, blocks, returns the answer.

Run it in the background when the user wants you to keep working meanwhile, and
watch for the terminal line:

```
Monitor pattern: ^\[t=\d+s\] (DONE|FAILED|TIMEOUT|ERROR|NOT_REVIEWED)
```

## Notes

- Requires `gh` (authenticated) and `jq`. `--coderabbit` also needs `uv` or `python3`.
- A run created seconds ago can 404 until GitHub catches up; the script retries
  through that for the first minute before giving up with exit 3.
- Each poll is one API call, plus one per job at the moment it completes.
