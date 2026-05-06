---
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

Invoke `scripts/wait-for.sh` once via the Bash tool.

```bash
scripts/wait-for.sh <kind> [args] [--profile quick|long]
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
| 0 | Done — success |
| 1 | Done — failed |
| 2 | Timed out (10 min cap) |
| 3 | Usage error |

## Foreground vs background

**Foreground (default)** — single Bash call, blocks until done. Use when the user is waiting on this result before doing anything else.

```
Bash: scripts/wait-for.sh coderabbit --profile long
```

**Background** — set `run_in_background: true` on the Bash call when the user wants Claude to keep working meanwhile. Then watch for the terminal stdout line via Monitor:

```
Monitor pattern: ^\[t=\d+s\] (DONE|FAILED|TIMEOUT)
```

This is the closest Claude Code has to a callback — Claude continues other work and gets notified when the line appears.

## Examples

User: "wait for CodeRabbit on this PR"
→ `scripts/wait-for.sh coderabbit --profile long`

User: "wait until CI is green on PR 142"
→ `scripts/wait-for.sh gh-checks 142`

User: "watch run 1234567890 and let me know when it's done"
→ `scripts/wait-for.sh gh-action 1234567890 --profile long`

## Notes

- Requires `gh` CLI authenticated and `jq`.
- CodeRabbit appears as a check run named `CodeRabbit` on the PR head SHA. If the bot is misconfigured and posts no check run, the script reports timeout.
- The 10-min cap is a hard limit. If the user expects something longer (full release pipeline, slow review queue), invoke the script multiple times rather than raising the cap — keeps each blocking call bounded.
