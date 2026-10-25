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
cannot see it. It reports through a commit status named `CodeRabbit`.
`--coderabbit` polls that status for `HEAD` on the same schedule, instead of
watching a run:

```bash
./scripts/wait-for-action.sh --coderabbit [--ttl 15m]
```

| Exit | Meaning |
|---|---|
| 0 | `DONE` — status `success`; the line carries its description, e.g. `Review completed` |
| 1 | `FAILED` — status `failure` or `error` |
| 2 | `TIMEOUT` — still `pending` |
| 3 | `ERROR` — no `CodeRabbit` status after a minute: no open PR for `HEAD`, or CodeRabbit is not installed on the repo |

`--coderabbit` takes no `--run-id` or `--repo`. Push first: the status is for
the pushed `HEAD` commit. Then read the review comments to resolve them. Read
both: findings outside the diff land in the review body, not inline.

```bash
gh api --paginate 'repos/{owner}/{repo}/pulls/<n>/comments' --jq '.[] | select(.user.login=="coderabbitai[bot]" and .in_reply_to_id==null) | {id, path, line: (.line // .original_line), body}'
gh api --paginate 'repos/{owner}/{repo}/pulls/<n>/reviews' --jq '.[] | select(.user.login=="coderabbitai[bot]" and .body!="") | {submitted_at, body}'
```

`line` is null once a later push moves the diff, so the first query falls back
to `original_line`. Both queries return every round; act on the newest.

A `success` description such as `Review rate limited` or `Review skipped`
means no review was posted. Report that; do not look for comments.

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
Monitor pattern: ^\[t=\d+s\] (DONE|FAILED|TIMEOUT|ERROR)
```

## Notes

- Requires `gh` (authenticated) and `jq`.
- A run created seconds ago can 404 until GitHub catches up; the script retries
  through that for the first minute before giving up with exit 3.
- Each poll is one API call, plus one per job at the moment it completes.
