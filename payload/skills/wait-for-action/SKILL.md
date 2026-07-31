---
name: wait-for-action
description: Wait for an asynchronous CI/review action (CodeRabbit review, GitHub PR checks, GitHub Actions run) without burning conversation tokens. Triggers on "wait for the review", "wait until CI passes", "wait for the action to finish", "let me know when CodeRabbit is done".
---

# wait-for-action

Polls an async action with adaptive backoff in a single blocking Bash call. Zero conversation tokens during the wait — the result lands once when the script exits.

## When to use

- User asks to wait for CodeRabbit to finish reviewing a PR
- User asks to wait for PR status checks to settle
- User asks to wait for a specific GitHub Actions run to complete

Do **not** poll in the conversation. Each turn replays full context — expensive. Hand the wait off to the script.

## How

Invoke the bundled `wait-for.sh` once via the Bash tool. Resolve the path
relative to this skill's directory:

```bash
./wait-for.sh <kind> [args] [--profile quick|long]
```

Kinds:

| Kind | Args | Profile |
|---|---|---|
| `coderabbit` | `[pr]` (auto-detect from current branch if omitted) | `long` |
| `gh-checks` | `[pr]` (auto-detect if omitted) | `quick` |
| `gh-action` | `<run-id> [repo]` | `quick` for fast jobs, `long` for full pipelines |

Profile picks the backoff schedule. Both cap at 10 min total.

- `quick` — intervals 30 30 60 60 90 120 120 120
- `long` — intervals 60 90 120 150 180 240

First probe always at t=30s regardless of profile (catches actions that fail to start).

Script emits one stdout line per probe: `[t=Xs] STATE detail`. Exit codes:

| Exit | Meaning |
|---|---|
| 0 | Done — success (for `coderabbit`, a review actually landed) |
| 1 | Done — failed |
| 2 | Timed out (10 min cap) |
| 3 | Usage error |
| 4 | Completed but produced **no review** — rate limited or skipped |

## Exit 4: green check, no review

**A green CodeRabbit check does not mean the PR was reviewed.** CodeRabbit reports
its check run `SUCCESS` whether it reviewed the diff or bailed with a notice:

- `Review rate limited` — fair-usage limit hit; the comment carries a
  "Next review available in: N minutes" window
- `Review skipped: excluded by label configuration` — config opted this PR out

Both are green. Neither is a review. The script now distinguishes them and exits
**4** with a `NOT-A-REVIEW` detail line rather than reporting success.

**Never report a PR as reviewed on exit 0 alone if you have not seen findings or
an explicit "Actionable comments posted" summary.** On exit 4, say plainly that
the review did not happen and surface the reason — the rate-limit notice is
signal, not noise: it tells the user their review budget is being consumed and
lets them decide when to spend the next one.

Exit 4 is terminal. Do not loop on it — re-running against the same commit hits
the same notice. Either wait out the stated window and re-trigger with
`@coderabbitai review`, or let the user decide. Re-triggering posts a public
comment on someone's repo, so ask before doing it on their behalf.

## Foreground vs background

**Foreground (default)** — single Bash call, blocks until done. Use when the user is waiting on this result before doing anything else.

**Background** — if the host tool supports background shell execution, run the
script in the background when the user wants the agent to keep working meanwhile.
Then watch for this terminal stdout line:

```
Monitor pattern: ^\[t=\d+s\] (DONE|FAILED|TIMEOUT)
```

This gives the host agent a callback-like signal while other work continues.

## Examples

User: "wait for CodeRabbit on this PR"
→ `wait-for.sh coderabbit --profile long`

User: "wait until CI is green on PR 142"
→ `wait-for.sh gh-checks 142`

User: "watch run 1234567890 and let me know when it's done"
→ `wait-for.sh gh-action 1234567890 --profile long`

## Notes

- Requires `gh` CLI authenticated and `jq`.
- CodeRabbit appears as a check run named `CodeRabbit` on the PR head SHA. If the bot is misconfigured and posts no check run, the script reports timeout.
- The 10-min cap is a hard limit. If the user expects something longer (full release pipeline, slow review queue), invoke the script multiple times rather than raising the cap — keeps each blocking call bounded.
