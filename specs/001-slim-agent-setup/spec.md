# Feature Specification: Slim the agent-setup skill

**Feature Branch**: `001-slim-agent-setup`

**Created**: 2026-10-14

**Status**: Draft

**Input**: User description: "Refactor and slim the agent-setup skill (skills/agent-setup): simplify
SKILL.md and scripts/render_agents.py per the follow-the-rules skill and constitution Principle IV
(Simplicity Over Coverage) — cut duplicated instructions, tighten the templates (builder, reviewer,
hall-monitor, orchestrate, instructions-block) and the value table — without changing what the
skill produces for Claude Code, Codex, and Cursor. Behavior must be preserved and provable
(constitution Principle II)." Amended: "Remove anything that references outside tooling or
anything other than agent definitions and managing them." Clarified: orchestrate becomes the main
wrapper, the way a session starts rather than a separate step; the instruction block is dropped;
the `follow-the-rules` dependency stays.

## Clarifications

### Session 2026-10-14

- Q: Is the orchestrate skill in scope, given it is not an agent definition? → A: Yes. It becomes
  the main wrapper: a session starts as the orchestrator instead of invoking it later.
- Q: Keep the instruction block written into `AGENTS.md` / `CLAUDE.md`? → A: No. Drop it.
- Q: Is `follow-the-rules` outside tooling? → A: No. It ships in this plugin; keep the dependency.
  Cut only the external install line.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agent definitions only, no outside tooling (Priority: P1)

A maintainer runs `/agent-setup` in a target repository. The skill writes the builder, reviewer,
and hall-monitor agent definitions and the orchestrator entry point for each chosen host, and
nothing else. It does not detect or mention development frameworks, MCP servers, or other tools,
and it does not edit the repository's instruction files.

**Why this priority**: This is the scope the user asked for. Every outside reference is text an
agent must read, act on, and keep current, for value that belongs to some other tool.

**Independent Test**: Run setup on a fixture repository that contains framework files, an MCP
config, and instruction files; check the resulting file tree and the skill's own text.

**Acceptance Scenarios**:

1. **Given** a fixture repository with `AGENTS.md` and `CLAUDE.md`, **When** setup runs for all
   three hosts, **Then** neither instruction file changes.
2. **Given** the refactored skill, templates, and generated files, **When** they are searched for
   named outside tools (Serena, gstack, mattpocock/skills, Spec Kit, `npx`), **Then** there are no
   matches.
3. **Given** setup completes, **When** the generated files are listed, **Then** they are exactly
   the three agent definitions and the orchestrator entry point for each chosen host.

---

### User Story 2 - Session starts as the orchestrator (Priority: P1)

A developer opens a session in a set-up repository. The session runs as the orchestrator from its
first turn: it already knows to cut work into lanes and start builders, reviewers, and
hall-monitors, without the developer invoking a skill or an instruction file telling it to.

**Why this priority**: The user named orchestrate as the main wrapper around the whole loop. With
the instruction block gone, how the session starts is the only thing that connects a developer to
the agents.

**Independent Test**: On each host, start a session in a set-up fixture repository and ask what
role it runs in and how it handles a multi-part spec.

**Acceptance Scenarios**:

1. **Given** a repository set up for a host, **When** a developer starts a session there in the
   way the setup report describes, **Then** the session runs with the orchestrator's instructions
   loaded, without a manual skill invocation.
2. **Given** an orchestrator session, **When** it receives a spec with independent parts, **Then**
   it starts one builder per lane and a reviewer and hall-monitor per finished lane.
3. **Given** a host that cannot start a session as a configured role, **When** setup runs for that
   host, **Then** the report says so and names the closest supported way to start the
   orchestrator there.

---

### User Story 3 - Leaner text, every kept rule intact (Priority: P2)

A maintainer reviewing the change can confirm that the rules the agents still need survived: each
in-scope rule the current templates and `SKILL.md` give is still given, in fewer words, and each
cut is listed with its reason.

**Why this priority**: Shorter prose can silently drop a rule (for example, "at most two review
rounds" or "reviewer never reviews code it wrote").

**Independent Test**: Build a rule inventory from the current text, mark each entry kept or cut;
check kept entries against the new text.

**Acceptance Scenarios**:

1. **Given** the rule inventory, **When** the refactored files are reviewed, **Then** every kept
   entry maps to a sentence in the new text and every cut entry names its reason.
2. **Given** the refactored templates, **When** they are rendered, **Then** no `{{` token remains
   and every generated file carries the agent-setup marker.

---

### User Story 4 - Clean upgrade and removal (Priority: P2)

A maintainer who set up a repository with the current version reruns setup, or removes it. Files
and instruction blocks the old version wrote are cleaned up, and nothing else is touched.

**Why this priority**: Repositories already carry the old instruction block and orchestrate skill
files. Leaving them behind would keep pointing sessions at a flow that no longer exists.

**Independent Test**: Set up a fixture with the current version, then rerun with the new one, and
separately remove with the new one.

**Acceptance Scenarios**:

1. **Given** a repository set up by the current version, **When** the new version runs setup,
   **Then** the old instruction blocks and any old artifacts the new version no longer writes are
   removed, and an instruction file left empty is deleted.
2. **Given** a set-up repository, **When** remove runs, **Then** every file and block any version
   wrote is gone, and files agent-setup did not write are untouched.

---

### User Story 5 - Parity is checkable later (Priority: P3)

A maintainer making a future change reruns one eval and sees whether output changed.

**Why this priority**: The constitution requires evidence for skill changes; a reusable eval keeps
the next edit honest too.

**Independent Test**: Run the eval on an unmodified checkout; it passes. Break one agent's metadata;
it fails and names the field.

**Acceptance Scenarios**:

1. **Given** the skill's `evals/` directory, **When** a maintainer runs the eval, **Then** it sets
   up fresh fixture repositories, asserts on the resulting files and their metadata, and reports
   pass or fail per case.

### Edge Cases

- A foreign file sits at an agent or orchestrator path: setup refuses and writes nothing unless
  forced.
- A repository still holds the legacy `orchestrator` agent from an older version: setup and remove
  both delete it.
- An instruction file holds an old agent-setup block plus other content: the block is removed, the
  other content is kept, leftover blank lines collapse.
- An optional value is empty: rendered text has no double spaces or dangling sentence.
- A value contains `'''`: the Codex agent file cannot hold it, so setup refuses rather than writing
  broken TOML.
- Only one host is chosen: no files appear for the other hosts.
- A required value is missing: setup exits non-zero and names the missing value.
- The repository already has a host setting for how sessions start: setup does not silently
  overwrite it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The skill MUST write only agent definitions (builder, reviewer, hall-monitor) and the
  orchestrator entry point, per chosen host, plus whatever host setting makes a session start as
  the orchestrator.
- **FR-002**: The skill, its templates, and generated files MUST NOT detect, name, or depend on
  outside tools: development frameworks, MCP servers, and package installers.
- **FR-003**: The skill MUST NOT write or edit the repository's instruction files (`AGENTS.md`,
  `CLAUDE.md`), except to remove blocks earlier versions wrote.
- **FR-004**: On each host, a session in a set-up repository MUST be able to start as the
  orchestrator without a manual skill invocation. Where a host cannot do this, the setup report
  MUST say so and name the closest supported way.
- **FR-005**: Builder, reviewer, and hall-monitor MUST keep their current name, tool list,
  preloaded skills, read-only flag, and sandbox mode on every host.
- **FR-006**: Builder and hall-monitor MUST keep depending on the `follow-the-rules` skill. The
  setup report MUST say on which hosts it is missing, without an install command for an outside
  installer.
- **FR-007**: Setup, rerun, force, and remove MUST keep their current semantics: rerun replaces
  only files agent-setup wrote; foreign files block setup unless forced; remove deletes only marked
  files and blocks; artifacts from earlier versions are cleared.
- **FR-008**: Every in-scope rule in the current `SKILL.md` and templates MUST appear in the
  refactored text, or be listed as an intentional cut with a stated reason.
- **FR-009**: No instruction may be stated twice across `SKILL.md` and the templates; each rule
  lives in the one file whose reader needs it.
- **FR-010**: The skill MUST stay user-invoked only on every host.
- **FR-011**: The skill MUST ship an `evals/` directory with cases for FR-001, FR-003, FR-005,
  FR-007, and the edge cases above, asserting on resulting files and metadata, not prose wording.
- **FR-012**: The refactored files MUST follow the `follow-the-rules` and `writing-for-agents`
  guidance.

### Key Entities

- **Template values**: the per-repository facts the skill gathers. After this change: project,
  conventions, gate and gate scopes, default branch, worktree note. Framework, implement, and
  review notes go away.
- **Agent definitions**: builder, reviewer, hall-monitor; one file per host, each with per-host
  permissions.
- **Orchestrator entry point**: the orchestrator's instructions plus whatever per-host setting makes
  a session start with them.
- **Legacy artifacts**: instruction blocks, the `orchestrator` agent, and any other file earlier
  versions wrote that the new version does not.
- **Rule inventory**: the distinct instructions the current text gives, each marked kept or cut.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Combined word count of `SKILL.md`, its reference files, and the templates drops by at
  least 40% from the 3,577-word baseline.
- **SC-002**: The renderer is no longer than its current 251 lines.
- **SC-003**: Zero matches for named outside tools in the skill, its templates, and generated
  output.
- **SC-004**: On 100% of supported hosts, a developer reaches an orchestrator session in one step
  from a fresh terminal, or the setup report names why not.
- **SC-005**: 100% of eval cases pass, and 100% of rule-inventory entries are kept or listed as
  cut.
- **SC-006**: A maintainer can check output after any future edit with one command, in under one
  minute.

## Assumptions

- Output parity with the current version is no longer the goal. The intended differences are: no
  instruction block, no framework or Serena content, and a new way to start the orchestrator.
  Agent metadata (FR-005) is still held to parity.
- The worktree note stays: lanes run in git worktrees, which is part of how the agents work, not an
  outside tool. Its Serena addendum goes.
- Host-native facts that decide whether agents load or can write (Codex project trust, Codex
  sandbox write roots) are part of managing agents. They stay as report-only checks.
- How each host starts a session as a configured role is unknown today and is resolved in the plan
  phase's research.
- The plugin-level `agents/hall-monitor.md` and the `follow-the-rules` skill are out of scope.
- The plugin version bump level (MINOR or MAJOR) is decided in the plan against the constitution's
  versioning rules.
