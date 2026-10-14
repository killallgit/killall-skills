---

description: "Task list for slimming the agent-setup skill"
---

# Tasks: Slim the agent-setup skill

**Input**: Design documents from `specs/001-slim-agent-setup/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/render-cli.md, quickstart.md

**Tests**: Requested. FR-011 and constitution Principle II require an `evals/` suite. Eval tasks come
first in each story and must fail before the matching implementation.

**Organization**: Grouped by user story (spec.md). Paths are relative to the repository root.
`SKILL_DIR` means `skills/agent-setup/`. The previous version is commit `d92095b`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 to US5, from spec.md

---

## Phase 1: Setup

**Purpose**: Branch, baseline, and the three start-up spikes that decide the orchestrator design

- [ ] T001 Create branch `001-slim-agent-setup` from `main`. Delete the Sync Impact Report comment at the top of `.specify/memory/constitution.md`. Commit `.gitignore`, `.worktreeinclude`, `.specify/`, `.claude/skills/speckit-*/`, and `specs/001-slim-agent-setup/` as `chore: add spec-kit scaffolding, constitution, and agent-setup spec`. Never stage `.claude/settings.local.json` or `.claude/worktrees/`
- [ ] T002 [P] Spike S1 (Claude Code), per quickstart.md step 4. Create a scratch git repo outside the project. Hand-write `.claude/agents/orchestrator.md`, the body of `SKILL_DIR/templates/orchestrate.tmpl.md` with values filled in and no `tools` key, plus `.claude/settings.json` set to `{"agent": "orchestrator"}`. Start `claude` and ask the quickstart question. Record in `specs/001-slim-agent-setup/spikes.md`: did it answer as the orchestrator, could it start a subagent, did built-in tool use still work
- [ ] T003 [P] Spike S2 (Codex). Same scratch setup with a `developer_instructions = '''…'''` top-level key in `.codex/config.toml`, a `builder` agent in `.codex/agents/builder.toml`, and the project trusted. Record in `specs/001-slim-agent-setup/spikes.md`: did the main session answer as the orchestrator, did a spawned builder claim the orchestrator role, did the builder's `sandbox_mode = "workspace-write"` let it write
- [ ] T004 [P] Spike S3 (Cursor). Same scratch setup with `.cursor/rules/orchestrator.mdc` (frontmatter `alwaysApply: true`) and `.cursor/agents/builder.md`. Record in `specs/001-slim-agent-setup/spikes.md`: did the main agent answer as the orchestrator, did a spawned builder claim the orchestrator role, does Cursor also list `.claude/agents/orchestrator.md` as a subagent
- [ ] T005 Apply the spike results. For each failed spike, switch that host to report-only in `specs/001-slim-agent-setup/research.md` (R1), in `specs/001-slim-agent-setup/data-model.md` (Orchestrator entry point), and in `specs/001-slim-agent-setup/contracts/render-cli.md` (Outputs per host). Stop and ask the user if S1 fails, since the Claude Code fallback (a `SessionStart` hook) changes the design

---

## Phase 2: Foundational

**Purpose**: The eval harness every story's evals run on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Create `SKILL_DIR/evals/fixtures/make_repo.py`. Follow the style of `skills/git-janitor/evals/fixtures/make_repo.py`: standard library only, Python 3.9, no classes with mutable fields. It builds a throwaway git repo in a temp dir from a fixture spec with these optional parts: `AGENTS.md`; a `CLAUDE.md` with or without an `@AGENTS.md` line; foreign files at given paths; a pre-existing `.claude/settings.json` with given keys; a pre-existing `.codex/config.toml` with given content, including a table header. It also takes a "set up by previous version" flag that runs `git show d92095b:skills/agent-setup/...` into a temp copy and executes that renderer
- [ ] T007 [P] Create `SKILL_DIR/evals/fixtures/vars.json` with synthetic values only (constitution Principle I). Keys: `project`, `conventions`, `gate`, `gate_scopes`, `default_branch`, `worktree_note`. Add a second file `SKILL_DIR/evals/fixtures/vars-legacy.json` that also has `framework_note` and `implement_note`, for the previous renderer
- [ ] T008 Create `SKILL_DIR/evals/run.py`. It reads `SKILL_DIR/evals/evals.json`, builds each case's fixture, runs `scripts/render_agents.py` with the case's flags, runs the case's assertions on the resulting files, exit code, and stdout, prints `PASS <case>` or `FAIL <case>: <assertion>`, and exits non-zero on any failure. Assertions are on state only, never prose wording. The whole suite must finish in under 60 seconds (SC-006)
- [ ] T009 Create `SKILL_DIR/evals/evals.json` with an empty `cases` list and a schema comment in `SKILL_DIR/evals/README.md` naming each case field: `id`, `fixture`, `args`, `expect_exit`, `expect_files`, `expect_absent`, `expect_unchanged`, `expect_metadata`. Run `python3 SKILL_DIR/evals/run.py` and confirm it exits 0 with no cases

**Checkpoint**: Harness runs; stories can start

---

## Phase 3: User Story 1 - Agent definitions only, no outside tooling (Priority: P1) 🎯 MVP

**Goal**: The skill writes only agent definitions and never mentions or edits outside tools or instruction files

**Independent Test**: Install for all three hosts into a fixture holding `AGENTS.md` and `CLAUDE.md`. Both instruction files stay byte-identical, the outside-tool grep finds nothing, and the file set matches the contract

### Evals for User Story 1

- [ ] T010 [US1] Add these cases to `SKILL_DIR/evals/evals.json`. Run them and confirm they fail:
  - `all-hosts`, `claude-only`, `codex-cursor`: exact agent file sets per contracts/render-cli.md.
  - `instruction-files-untouched`: `AGENTS.md` and `CLAUDE.md` byte-identical after install.
  - `agent-metadata`: Claude `tools` "Read, Grep, Glob, Bash, Edit, Write, Skill" for builder and "Read, Grep, Glob, Bash, Skill" for reviewer and hall-monitor; Claude `skills` "follow-the-rules" for builder and hall-monitor only; Cursor `readonly` false, false, true; Codex `sandbox_mode` "workspace-write", "workspace-write", "read-only".
  - `no-outside-tools`: case-insensitive grep of every generated file for `serena|gstack|mattpocock|spec kit|npx` finds nothing.
  - `missing-required`: an empty `gate` exits non-zero, names `gate`, and writes nothing.
  - `toml-quote`: a value containing `'''` exits non-zero and writes nothing.
  - `empty-optional`: an empty `gate_scopes` leaves no double space in any generated file.
  - `foreign-agent`: a foreign `.claude/agents/builder.md` makes install exit non-zero, list the path, and write nothing. With `--force`, the same fixture is replaced.

### Implementation for User Story 1

- [ ] T011 [US1] In `SKILL_DIR/scripts/render_agents.py`, delete `BLOCK_TEMPLATE`, `write_block`, `instruction_files`, `IMPORTS_AGENTS`, and the `--instructions` flag. Set `REQUIRED = ("project", "conventions", "gate", "default_branch", "worktree_note")` and `OPTIONAL = ("gate_scopes",)`. Keep the `TOKEN` rule that drops the leading space of an empty value. Keep block *removal* (`BLOCK`, `files_with_block`) for US4
- [ ] T012 [P] [US1] Delete `SKILL_DIR/templates/instructions-block.tmpl.md` and `SKILL_DIR/references/serena.md`, and the empty `SKILL_DIR/references/` folder
- [ ] T013 [P] [US1] In `SKILL_DIR/templates/builder.tmpl.md`, remove `{{implement_note}}`. Change the description to say it is started only by the orchestrator, not "the orchestrate skill". Keep the frontmatter permission keys unchanged
- [ ] T014 [P] [US1] In `SKILL_DIR/templates/reviewer.tmpl.md`, remove `{{review_note}}` and change the description the same way. Keep the frontmatter permission keys unchanged
- [ ] T015 [P] [US1] In `SKILL_DIR/templates/hall-monitor.tmpl.md`, change the description the same way. Keep the frontmatter permission keys unchanged
- [ ] T016 [US1] In `SKILL_DIR/SKILL.md`, remove the Framework section (rules S6–S8), the `framework_note`, `implement_note`, and `review_note` rows, the Serena paragraph (S13), the instruction-block check (S18), the instruction-block sentences in step 2, and the `npx` install line in step 3 (S17 keeps the per-host report only). Per data-model.md, keep S1–S5, S9–S12, S14–S17, and S19–S21
- [ ] T017 [US1] Run `python3 SKILL_DIR/evals/run.py` and make every US1 case pass

**Checkpoint**: US1 complete. agent-setup writes only the three agents, with no outside references

---

## Phase 4: User Story 2 - Session starts as the orchestrator (Priority: P1)

**Goal**: A session in a set-up repository runs as the orchestrator from its first turn, on every host whose spike passed

**Independent Test**: Install for all hosts, then repeat the quickstart.md step 4 check on the generated files instead of the hand-written spike files

### Evals for User Story 2

- [ ] T018 [US2] Add these cases to `SKILL_DIR/evals/evals.json`, limited to hosts whose spike passed (T005). Run them and confirm they fail:
  - `claude-entry`: `.claude/agents/orchestrator.md` exists with the marker and no `tools` key, and `.claude/settings.json` has `"agent": "orchestrator"`.
  - `claude-settings-preserved`: other keys in an existing `.claude/settings.json` are kept.
  - `claude-settings-foreign`: an existing `"agent": "other"` blocks install without `--force`, and nothing is written.
  - `codex-entry`: `.codex/config.toml` starts with the marker-wrapped `developer_instructions` block, the original content follows unchanged after it, and the file parses as TOML (check with `tomllib` only when available, else skip that assertion).
  - `codex-foreign`: an unmarked `developer_instructions` blocks install.
  - `cursor-entry`: `.cursor/rules/orchestrator.mdc` has `alwaysApply: true` and the marker.
  - `report-only-host`: a host switched to report-only gets no start-up setting.

### Implementation for User Story 2

- [ ] T019 [US2] `git mv SKILL_DIR/templates/orchestrate.tmpl.md SKILL_DIR/templates/orchestrator.tmpl.md`. Then rewrite it:
  - Frontmatter `name: orchestrator`, with a description saying it is the session's own role.
  - Replace "This loop stays in the main session because a subagent cannot start further subagents" with a statement that it *is* the main session (rule T19).
  - Add rule R4: when the work has no independent parts, make the single small change yourself; run lanes only for parallel work.
  - Remove `{{framework_note}}` (T20), the `npx` install line (T22 keeps the ask-the-user part), the project-root tool paragraph (T23), and the loop diagram, since the numbered steps already state it (T21).
- [ ] T020 [US2] In `SKILL_DIR/scripts/render_agents.py`, render `orchestrator.tmpl.md` per host. Claude Code: an agent file at `.claude/agents/orchestrator.md` with `name` and `description` only, so it inherits all tools including `Agent`. Codex: the body as a TOML literal for `developer_instructions`. Cursor: `.cursor/rules/orchestrator.mdc` with frontmatter `description` and `alwaysApply: true`. Remove `SKILL_TEMPLATE` and `skill_path`
- [ ] T021 [US2] In `SKILL_DIR/scripts/render_agents.py`, add start-up setting writes per research.md R2:
  - `.claude/settings.json`: load the JSON, set only `agent`, and write it back with 2-space indent.
  - `.codex/config.toml`: prepend a block between `# agent-setup:start` and `# agent-setup:end` comment lines. Replace that block on rerun.
- [ ] T022 [US2] In `SKILL_DIR/scripts/render_agents.py`, move every refusal into one preflight that runs before the first write: foreign agent files, a foreign `agent` setting, unmarked `developer_instructions`, and a foreign `.mdc` rule. `--force` overrides all of them (contracts/render-cli.md, Exit behavior)
- [ ] T023 [US2] In `SKILL_DIR/SKILL.md`, add rule S22 to the Report step: per host, how a session starts as the orchestrator (`claude`, or `claude --agent orchestrator` to override; Codex in a trusted project; Cursor through the always-apply rule), and, for a report-only host, the closest supported way. Update step 2's list of written files
- [ ] T024 [US2] Run `python3 SKILL_DIR/evals/run.py` and make every US1 and US2 case pass

**Checkpoint**: US1 and US2 complete. This is the shippable core

---

## Phase 5: User Story 3 - Leaner text, every kept rule intact (Priority: P2)

**Goal**: At most 2,146 words across `SKILL.md` and templates (SC-001), renderer at most 251 lines (SC-002), every kept rule still present

**Independent Test**: The `text-budget` eval passes, and every kept row in the data-model.md rule inventory names the sentence that now holds it

### Evals for User Story 3

- [ ] T025 [US3] Add a `text-budget` case to `SKILL_DIR/evals/evals.json`, and support for it in `SKILL_DIR/evals/run.py`. It asserts total `wc -w` of `SKILL_DIR/SKILL.md` and `SKILL_DIR/templates/*.tmpl.md` is ≤ 2146, `SKILL_DIR/scripts/render_agents.py` is ≤ 251 lines, and the outside-tool grep of `SKILL_DIR` (excluding `evals/`) finds nothing. Run it and record the current numbers

### Implementation for User Story 3

- [ ] T026 [P] [US3] Tighten `SKILL_DIR/templates/builder.tmpl.md`, `SKILL_DIR/templates/reviewer.tmpl.md`, and `SKILL_DIR/templates/hall-monitor.tmpl.md` per the `writing-for-agents` skill. Keep rules T1–T4, T7–T10, and T12–T17; cut T6. State the absolute-worktree-path rule once per agent (research.md R3)
- [ ] T027 [P] [US3] Tighten `SKILL_DIR/templates/orchestrator.tmpl.md`. Keep rules T18, T19, T21, T22, and T24–T26. Drop the "worktree path is absolute" explanation from the brief list, because each lane agent states it (R3)
- [ ] T028 [P] [US3] Tighten `SKILL_DIR/SKILL.md`: one sentence per rule, no restated intro list of what each agent does (the agent descriptions carry that), and a value table with six rows
- [ ] T029 [US3] Simplify `SKILL_DIR/scripts/render_agents.py` per the `follow-the-rules` skill: remove the module docstring that restates the code, fold `ours`/`foreign` and any single-use helpers, keep pure functions. Re-run all evals
- [ ] T030 [US3] Fill the "Where" column of every kept row in `specs/001-slim-agent-setup/data-model.md` with the file and section that now holds it. Confirm every cut row has a reason (SC-005). Make the `text-budget` case pass

**Checkpoint**: Text within budget and rule inventory reconciled

---

## Phase 6: User Story 4 - Clean upgrade and removal (Priority: P2)

**Goal**: Rerun and remove clean up everything any version wrote, and nothing else

**Independent Test**: Set up a fixture with renderer `d92095b`, rerun with the new one, then remove. Only foreign content is left

### Evals for User Story 4

- [ ] T031 [US4] Add these cases to `SKILL_DIR/evals/evals.json`. Run them and confirm they fail:
  - `upgrade-from-previous`: a fixture set up by `d92095b` with all hosts. The new install removes every `<!-- agent-setup:start -->` block, the `orchestrate` skill at `.claude/skills/orchestrate/`, `.agents/skills/orchestrate/`, and `.cursor/skills/orchestrate/`, and any `orchestrator` agent in `.codex/agents/` or `.cursor/agents/`. An instruction file left empty is deleted, and other content in instruction files is kept with blank lines collapsed.
  - `remove-all`: after install, `--remove` leaves no marked file, no `agent` key written by agent-setup, and no marker block in `.codex/config.toml`. A settings file left as `{}` or empty is deleted, and foreign files are untouched.
  - `remove-keeps-foreign`: a foreign `"agent"` value and unmarked TOML survive `--remove`.

### Implementation for User Story 4

- [ ] T032 [US4] In `SKILL_DIR/scripts/render_agents.py`, replace `LEGACY_AGENTS` with a legacy list that names exact paths per host: the `orchestrate` skill folders, and `orchestrator` agents in `.codex/agents/` and `.cursor/agents/` only. `.claude/agents/orchestrator.md` is now the live entry point and must not be in the legacy list. Install and remove both clear legacy paths that carry the marker
- [ ] T033 [US4] In `SKILL_DIR/scripts/render_agents.py`, run legacy block removal on install as well as remove, reusing `files_with_block`. In remove, delete the `agent` key only when its value is `orchestrator` and agent-setup wrote it, and delete the `.codex/config.toml` marker block. Delete a settings or config file left empty
- [ ] T034 [US4] Run `python3 SKILL_DIR/evals/run.py` and make every case pass

**Checkpoint**: Upgrades and removal are safe on repositories set up by earlier versions

---

## Phase 7: User Story 5 - Parity is checkable later (Priority: P3)

**Goal**: One command compares the current renderer's agent metadata with any previous ref

**Independent Test**: `compare_previous.py d92095b` passes on the finished branch. Changing one template's `codex_sandbox` makes it fail and name the field

- [ ] T035 [US5] Create `SKILL_DIR/evals/compare_previous.py <ref>`. It extracts `SKILL_DIR` at `<ref>` with `git archive` into a temp dir, renders both versions into fresh fixtures with all hosts (passing `vars-legacy.json` to the old one), parses builder, reviewer, and hall-monitor metadata on each host, and prints each difference as `<host>/<agent>.<field>: <old> -> <new>`. It exits non-zero on any difference and reports file-set differences without failing on them
- [ ] T036 [US5] Run `python3 SKILL_DIR/evals/compare_previous.py d92095b` and confirm it exits 0. Break `codex_sandbox` in `SKILL_DIR/templates/reviewer.tmpl.md`, confirm it fails naming `codex/reviewer.sandbox_mode`, then revert. Time `python3 SKILL_DIR/evals/run.py` and confirm it is under 60 seconds

**Checkpoint**: All stories complete

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T037 [P] Update the frontmatter `description` in `SKILL_DIR/SKILL.md` to name the orchestrator and the three agents and drop "wire them into its instruction files". Update `short_description` in `SKILL_DIR/agents/openai.yaml` to match. Keep `disable-model-invocation: true` and `allow_implicit_invocation: false` (FR-010)
- [ ] T038 [P] Rewrite the "Agent setup" section of `README.md`: an orchestrator that the session starts as, three lane agents, no framework block, and how to start on each host. Update the host matrix if what a host receives changed
- [ ] T039 Run quickstart.md steps 1–3 and the outside-tool grep across `SKILL_DIR`, `README.md`, and generated fixture output
- [ ] T040 Run the `hall-monitor` and `comment-janitor` agents on the branch diff and fix the findings
- [ ] T041 Bump the version to `3.0.0` in `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, and `.cursor-plugin/plugin.json` (research.md R6), as its own commit `chore: bump plugin version to 3.0.0`
- [ ] T042 Open a PR to `main`. In the body, include the spike results from `specs/001-slim-agent-setup/spikes.md`, the eval output, the before and after word and line counts, and the rule-inventory verdicts with each cut and its reason (FR-008)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 first. T002–T004 run in parallel, and T005 waits for all three
- **Foundational (Phase 2)**: Depends on T001. T006 and T007 run in parallel, then T008, then T009
- **US1 (Phase 3)**: Depends on Phase 2
- **US2 (Phase 4)**: Depends on US1 (both rewrite `render_agents.py` and `SKILL.md`) and on T005
- **US3 (Phase 5)**: Depends on US2. It trims the text US1 and US2 produced
- **US4 (Phase 6)**: Depends on US2, because the legacy list must exclude the new `.claude/agents/orchestrator.md`. It can run in parallel with US3 only if two builders do not edit `render_agents.py` at once; T029 and T032–T033 conflict, so run them in sequence
- **US5 (Phase 7)**: Depends on Phase 2 and US1. It can run any time after US1
- **Polish (Phase 8)**: Depends on all stories

### Within Each User Story

- Evals are written and seen to fail before implementation
- Template and file deletions marked [P] touch separate files
- `render_agents.py` and `SKILL.md` edits are sequential

### Parallel Opportunities

- T002, T003, T004: three host spikes
- T006, T007: fixture builder and vars files
- T012, T013, T014, T015: separate template and reference files
- T026, T027, T028: separate text files
- T035 (US5) alongside US3 or US4, since it creates a new file
- T037, T038: separate docs

---

## Parallel Example: User Story 1

```bash
# After T011, in parallel:
Task: "Delete templates/instructions-block.tmpl.md and references/serena.md (T012)"
Task: "Remove {{implement_note}} and update description in templates/builder.tmpl.md (T013)"
Task: "Remove {{review_note}} and update description in templates/reviewer.tmpl.md (T014)"
Task: "Update description in templates/hall-monitor.tmpl.md (T015)"
```

## Parallel Example: Setup spikes

```bash
Task: "Spike S1 Claude Code orchestrator start-up (T002)"
Task: "Spike S2 Codex developer_instructions start-up (T003)"
Task: "Spike S3 Cursor always-apply rule start-up (T004)"
```

---

## Implementation Strategy

### MVP First

1. Phase 1, including the spikes. T005 may change US2's scope
2. Phase 2 harness
3. US1: agent-setup writes only agents, with no outside references
4. **Stop and validate**: run the evals. US1 alone is not releasable, because the old orchestrate skill and the block are gone with no replacement, so continue straight to US2
5. US2: the orchestrator entry point. US1 and US2 together form the smallest releasable change

### Incremental Delivery

1. Setup, Foundational, US1, then US2: the releasable core
2. US3: text budget
3. US4: safe upgrade for existing repos. Required before release, because existing repos carry the old block
4. US5: reusable parity check
5. Polish and release as 3.0.0

---

## Notes

- `SKILL_DIR` = `skills/agent-setup/`; previous version = `d92095b`
- Every eval asserts on files, metadata, exit codes, or stdout lines, never on prose (constitution Principle II)
- Fixture values are synthetic (constitution Principle I)
- Commit after each task or logical group, using Conventional Commits
