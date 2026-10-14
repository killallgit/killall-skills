# Research: Slim the agent-setup skill

## R1. How a session starts as the orchestrator, per host

### Claude Code

- **Decision**: Write the orchestrator as an agent definition, `.claude/agents/orchestrator.md`,
  and set `"agent": "orchestrator"` in the repository's `.claude/settings.json`.
- **Rationale**: Claude Code runs the main thread as a named agent from this setting; `claude
  --agent <name>` overrides it per session (flag confirmed on Claude Code 2.1.299 via `claude
  --help`). The file is committed, so every clone starts the same way. The main thread keeps the
  `Agent` tool when `tools` is omitted, so it can still start builders, reviewers, and
  hall-monitors.
- **Risk**: The docs say an agent body replaces the default system prompt, the way
  `--system-prompt` does. That drops built-in tool guidance. **Spike S1** verifies behavior in a
  fixture before the renderer depends on it.
- **Fallback if S1 fails**: a `SessionStart` hook whose `additionalContext` carries the
  orchestrator body. It keeps the default prompt, but caps context at 10,000 characters and writes
  a hook into shared settings.
- **Alternatives rejected**: output styles (cannot gate tools); `--append-system-prompt-file` (needs
  a per-machine alias, not committed).

### Codex

- **Decision**: Write a top-level `developer_instructions` key in the repository's
  `.codex/config.toml`, wrapped in agent-setup marker comments.
- **Rationale**: Documented as additional developer instructions injected into the session. The
  primary session can spawn the custom agents in `.codex/agents/`.
- **Risks**: (a) Project-scoped config loads only for a trusted project; the skill already reports
  trust (rule S19). (b) Spawned agents may inherit the parent's `developer_instructions`, leaking
  the orchestrator role into lanes. (c) An agent file's `sandbox_mode` may not override the
  parent's. **Spike S2** checks (b) and (c).
- **Fallback if S2 shows leakage**: report-only on Codex. The report names the orchestrator
  instruction file and tells the user to start Codex with it; FR-004 allows this.
- **Alternatives rejected**: `model_instructions_file` (replaces Codex's built-in instructions);
  profiles (ignored in project config); a named main agent (not supported).

### Cursor

- **Decision**: Write `.cursor/rules/orchestrator.mdc` with `alwaysApply: true`.
- **Rationale**: Always-apply rules load in the editor and the CLI with no user action. The main
  agent spawns subagents from `.cursor/agents/` through its Task tool.
- **Risks**: (a) Always-apply rules may reach subagents, leaking the orchestrator role. (b) Cursor
  also reads `.claude/agents/`, so it sees `orchestrator.md` as a subagent too. **Spike S3**
  checks both.
- **Fallback if S3 shows leakage**: report-only, as for Codex.
- **Alternatives rejected**: Custom Modes (manual pin, no file); `--mode` (built-in modes only).

### Spike results (spikes.md)

- S1, S2, and S3 all pass; no host is report-only.
- Cursor's always-apply rule reached a spawned builder until the orchestrator body opened with a
  guard sentence telling subagents to ignore it. The template carries that sentence on every host.
- Codex builders inherit a stricter parent sandbox; the report tells the user builders need the
  main session in workspace-write.

### Source quality

The Claude Code findings come from the official docs and the local CLI. The Codex and Cursor
findings come from a web-research pass whose sources were not opened directly here; treat them as
leads. Spikes S2 and S3 are the evidence.

## R2. Editing files the user also owns

- **Decision**: For `.claude/settings.json`, load the JSON, set only `agent`, and write it back. For
  `.codex/config.toml`, prepend a marker-wrapped block, because top-level keys must precede the
  first table header. Refuse when the key is already set to something agent-setup did not write,
  unless `--force`. Remove deletes only the key or block it wrote, and deletes the file when
  nothing else remains.
- **Rationale**: Matches the existing ownership rule: agent-setup never changes what it did not
  write.
- **Alternatives rejected**: A TOML library. `tomllib` is read-only and needs Python 3.11; the
  maintainer's default `python3` is 3.9.6, and the skill installs nothing.

## R3. Where the agents' shared rules live

- **Decision**: State the absolute-worktree-path rule once in each lane agent; delete it from the
  orchestrator's brief list.
- **Rationale**: Each agent reads only its own file, so per-agent repetition is the one place a rule
  must repeat (FR-009 counts files whose reader needs the rule). The orchestrator only needs to
  pass the path.

## R4. Small changes when every session is the orchestrator

- **Decision**: The orchestrator makes a single small change itself when the work has no
  independent parts; it runs lanes only when parallel work exists.
- **Rationale**: The old instruction block said "a single small change stays in the main session".
  Now the main session is the orchestrator, so without this rule every typo fix would cost a
  builder, a reviewer, and a hall-monitor.
- **Trade-off**: It reverses "you write no product code" for small changes. The orchestrator text
  states the boundary explicitly.

## R5. Proving parity

- **Decision**: An eval under `skills/agent-setup/evals/` builds fixture repositories, runs the
  renderer, and asserts on files and parsed metadata. A one-off comparison runs the current
  renderer from git history against the same fixtures and diffs agent metadata.
- **Rationale**: Mirrors the existing `skills/git-janitor/evals/` layout (`evals.json`, checker
  scripts, fixture builders). Asserts on state, never prose (constitution Principle II).

## R6. Plugin version bump

- **Decision**: MAJOR. Generated repositories lose the `orchestrate` skill and the instruction
  block, and the way users start the loop changes.
- **Rationale**: The constitution's Host Compatibility Constraints count a breaking change in
  invocation as MAJOR.
