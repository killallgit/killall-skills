# Implementation Plan: Slim the agent-setup skill

**Branch**: `001-slim-agent-setup` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-slim-agent-setup/spec.md`

## Summary

Cut agent-setup down to agent definitions and their management. Remove framework detection, the
Serena reference, the `npx` install line, and the instruction block. Replace the `orchestrate` skill
with an orchestrator that a session starts as: on Claude Code an agent named by the `agent`
setting, on Codex a `developer_instructions` block in project config, and on Cursor an
always-apply rule. Each host's mechanism is gated by a spike (research.md, R1). A host whose spike
fails gets report-only start-up instructions. Keep builder, reviewer, and hall-monitor metadata at
parity. Prove it with an eval suite.

## Technical Context

**Language/Version**: Python 3.9+ (renderer, evals); Markdown and TOML (templates, generated files)

**Primary Dependencies**: Python standard library and `git` only; the skill installs nothing

**Storage**: Files in the target repository

**Testing**: Eval scripts under `skills/agent-setup/evals/`, following the `git-janitor` evals
layout; fixture repositories built in temporary directories

**Target Platform**: Claude Code, Codex, Cursor (beta), on macOS and Linux

**Project Type**: Agent skill with a bundled renderer script

**Performance Goals**: Eval suite runs in under one minute (SC-006)

**Constraints**: Text at most 2,146 words (SC-001); renderer at most 251 lines (SC-002); no outside
tool names (SC-003); a failed run writes nothing

**Scale/Scope**: One skill: `SKILL.md`, four templates, one script, one eval suite

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
| --- | --- | --- |
| I. Public by Default | pass | Fixtures use synthetic repos and values; no personal or work data |
| II. Evaluation-Driven Optimization | pass | FR-011 adds `evals/` asserting on files and metadata; spikes record evidence in the PR |
| III. Supported Hosts Only | pass | Claude Code, Codex, Cursor only; per-host mechanism and fallback stated in research.md |
| IV. Simplicity Over Coverage | pass, one justified addition | Framework, Serena, and block logic removed; start-up settings editing added (see Complexity Tracking) |
| V. Agent-Readable Instructions | pass | Rewrite follows `writing-for-agents`; rule inventory in data-model.md |
| Host Compatibility Constraints | action | MAJOR plugin bump across all three manifests (research.md, R6); README "Agent setup" section rewritten in the same change |
| Development Workflow | action | Work on branch `001-slim-agent-setup`, PR to `main`, separate version-bump commit |

Post-design re-check: unchanged. The design adds no host, no dependency, and no outside tool.

## Project Structure

### Documentation (this feature)

```text
specs/001-slim-agent-setup/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── render-cli.md
├── checklists/
│   └── requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
skills/agent-setup/
├── SKILL.md                     # rewritten: Look, Write, Check, Report; no framework or Serena
├── agents/openai.yaml           # unchanged: keeps Codex from invoking the skill
├── scripts/render_agents.py     # block logic out; start-up settings and legacy cleanup in
├── templates/
│   ├── builder.tmpl.md          # trimmed
│   ├── reviewer.tmpl.md         # trimmed
│   ├── hall-monitor.tmpl.md     # trimmed
│   ├── orchestrator.tmpl.md     # replaces orchestrate.tmpl.md
│   └── instructions-block.tmpl.md  # deleted
├── references/serena.md         # deleted, with its folder
└── evals/
    ├── evals.json
    ├── run.py
    ├── compare_previous.py
    └── fixtures/make_repo.py

README.md                        # "Agent setup" section rewritten
.claude-plugin/plugin.json       # version bump
.codex-plugin/plugin.json        # version bump
.cursor-plugin/plugin.json       # version bump
```

**Structure Decision**: Keep the existing skill layout. Add `evals/` beside `SKILL.md`, as the
constitution requires. Rename the orchestrate template to `orchestrator` to match the role it now
plays. Each host writes it in its own form: an agent file, a TOML block, or an `.mdc` rule.

## Phases after this plan

1. **Spikes first** (quickstart.md, step 4): S1 to S3 decide which hosts get a start-up setting.
   They need hand-written fixture files only, not the new renderer.
2. **Evals red**: write `evals/` against the contract in contracts/render-cli.md.
3. **Renderer**: remove block logic and the `--instructions` flag; add the orchestrator outputs,
   start-up settings, and legacy cleanup; keep the check-everything-before-writing behavior.
4. **Text**: rewrite `SKILL.md` and the templates against the rule inventory in data-model.md.
5. **Release**: README, three manifests, PR with spike results and the rule inventory verdicts.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| Renderer edits two files the user may also own (`.claude/settings.json`, `.codex/config.toml`) | FR-004: a session must start as the orchestrator with no manual step, and these files are the only committed switch on those hosts | Report-only on every host leaves the user to configure each host by hand. That fails US2 wherever a host supports a switch |
