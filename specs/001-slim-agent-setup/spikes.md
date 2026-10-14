# Spikes: starting a session as the orchestrator

Run 2026-10-14 in throwaway repositories outside the project. Each held hand-written start-up files
and the builder, reviewer, and hall-monitor agents rendered by agent-setup at `d92095b`. Every run
was headless and single-sample, so treat the results as evidence, not proof.

| Spike | Host and version | Mechanism | Result |
| --- | --- | --- | --- |
| S1 | Claude Code 2.1.299, `claude -p` | `.claude/agents/orchestrator.md` with no `tools` key, and `"agent": "orchestrator"` in `.claude/settings.json` | **Pass** |
| S2 | Codex CLI 0.162.1, `codex exec`, project trusted with `-c projects."<path>".trust_level="trusted"` | Top-level `developer_instructions` in `.codex/config.toml`, wrapped in marker comments | **Pass**, with a sandbox note |
| S3 | Cursor Agent CLI 2026.04.17, `cursor-agent -p --trust` | `.cursor/rules/orchestrator.mdc` with `alwaysApply: true` | **Pass with a guard sentence**; fails without it |

## S1, Claude Code

- The main session described itself as the orchestrator for the fixture project, and said it
  writes no product code.
- It started the `builder` subagent. The builder described itself as the lane builder, so the
  orchestrator role did not leak.
- Built-in tools still worked under the agent: Read succeeded. Bash `git` commands were blocked
  pending approval in both the agent run and a control run without the `agent` setting, so that is
  the headless permission setup, not the agent.

## S2, Codex

- The main session described itself as the repository's orchestrator.
- It spawned `builder`, which did not claim the orchestrator role.
- With the parent session on `-s read-only`, a builder asked to create a file could not: the
  builder's own `sandbox_mode = "workspace-write"` does not loosen a stricter parent sandbox. The
  current version has the same behavior. Builders can write only when the main session runs with
  workspace-write, which is Codex's interactive default. The setup report must say so.

## S3, Cursor

- The main agent described itself as the orchestrator.
- Cursor listed `orchestrator` among its subagents, because it also reads `.claude/agents/`.
- Without a guard, a spawned builder reported that its instructions told it it was the orchestrator
  (`ORCH=yes`). The always-apply rule reaches subagents.
- With this sentence added at the top of the rule body, the builder reported `ORCH=no` and the main
  agent still acted as the orchestrator: "These instructions are for the main session only. If you
  were started as a subagent, such as a builder, reviewer, or hall-monitor, ignore this file and
  follow your own instructions." The second run's question was worded slightly differently from
  the first.
- The first builder spawn failed once with `NGHTTP2_ENHANCE_YOUR_CALM`, which was transient; the
  rerun succeeded.

## Decisions

- No host switches to report-only.
- The orchestrator template opens with the guard sentence on every host. Claude Code does not need
  it, but one body for all hosts is simpler than a per-host variant, and Codex may also pass
  `developer_instructions` to spawned agents.
- The setup report adds the Codex sandbox note.
