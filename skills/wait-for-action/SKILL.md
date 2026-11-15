---
name: wait-for-action
description: Wait for observable GitHub PR activity to settle in one read-only call. Discovers CI and bot reviewers, including activity outside Actions. Never triggers reviews or decides what is required. Use after a push or when checking what is still running.
---

# Wait for action

One job: observe a PR until its visible work settles, fails, or times out.

```bash
python3 scripts/wait_for_action.py [--pr N] [--repo OWNER/REPO] [--ttl 15m]
```

- `--pr`: defaults to the current branch's PR. Pass it outside a checkout.
- `--repo`: defaults to the current repository. With no `--pr`, resolves the
  current branch's PR in that repository.
- `--ttl`: total budget, including API calls; accepts `45s`, `15m`, `1h`, or seconds.
- `--log-dir`: optional artifact directory; otherwise creates a private unique one.

Requires authenticated `gh` 2.48+ and Python 3.10+. Use one blocking call, or
background it when the host's foreground timeout is shorter than the budget.
Do not replace it with conversational polling.

## Fixed behavior

- Poll every five seconds. Stop immediately on an observed failure.
- Discover check runs, commit statuses, Actions workflows, bot reviews, review
  requests, and bot comments. Follow pagination and changes to the PR head.
- Keep distinct check suites and overlapping running workflows separate.
  Discard completed results only when evidence establishes supersession.
- Report completed check titles, including CodeRabbit skip/rate-limit notices.
  Never post comments, request a review, retry a reviewer, or change PR state.
- Count only observable running work as pending. A review request or bot comment
  alone does not prove work started or establish a current-head review verdict.
- Require ten seconds of stable observations before settling. This cannot rule
  out work that has not registered yet, especially immediately after a push.
- Stop after three consecutive discovery errors within the total budget; never
  treat an unreadable source as a successful result.

## Results

| Exit | Result | Meaning |
|---|---|---|
| 0 | `DONE` | Observed activity settled; not merge approval or a review verdict |
| 1 | `FAILED` | An observed check, status, or workflow failed or was cancelled |
| 2 | `TIMEOUT` | Activity did not settle within the budget; also invalid CLI arguments from argparse |
| 3 | `ERROR` | Discovery repeatedly failed |
| 5 | `NONE` | No current-head execution or submitted bot review observed |

`NONE` is not a missing-review failure. Neither `NONE` nor `DONE` proves all
expected checks have registered. The caller enforces required CI and reviews;
installation or discovery of a reviewer never makes it required.

The `ARTIFACTS` line gives the directory containing `activity.json` (raw evidence),
`summary.json` (classified activity), and `poll.log`. Inspect those files for
specific findings rather than dumping full logs into context. This script does
not fetch job logs, resolve findings, or decide whether to merge.
