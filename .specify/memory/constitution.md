# killall-skills Constitution

## Core Principles

### I. Public by Default

killall-skills is a personal registry published in a public repository. Every committed file is
public.

- Commits MUST NOT contain personal details, employer or client names, internal hostnames,
  private repository names, credentials, or work-specific procedures.
- Examples, fixtures, and eval data MUST use generic or synthetic values.
- Skills that need organization-specific knowledge MUST take it from the target repository at
  run time, not from text baked into the skill.

Rationale: anything pushed here is indexed and cached. A leak cannot be reliably undone.

### II. Evaluation-Driven Optimization

The registry exists to make skills measurably better through evaluation and experimentation.

- A change that claims to improve a skill's behavior MUST cite evidence: an eval run, a
  before/after comparison, or a recorded experiment.
- New skills with deterministic, checkable outcomes MUST ship an `evals/` directory beside
  `SKILL.md` with at least one eval case and a checker that asserts on resulting state.
- Evals MUST assert on observable outcomes (files, git state, exit codes, structured output),
  not on the wording of agent prose.
- A change that regresses an existing eval MUST NOT merge until the eval passes again or the
  eval is amended with a stated reason.
- Experiments that fail are still recorded in the commit or PR description, so the same
  dead end is not explored twice.

Rationale: without measurement, "optimized" is opinion. Evals turn skill edits into
falsifiable claims.

### III. Supported Hosts Only

The registry supports exactly three agent hosts: Claude Code, Codex, and Cursor (beta).

- Every skill in `skills/` MUST work on Claude Code and Codex. Cursor support is best effort
  while it is beta.
- Host-specific behavior (invocation syntax, frontmatter, tool names) MUST be stated in the
  skill or the README host matrix, not assumed.
- Agents in `agents/` MAY be Claude Code only; the README host matrix MUST say so.
- Support for another host MUST NOT be added without amending this principle.

Rationale: a small host surface keeps every skill testable on every host it claims to support.

### IV. Simplicity Over Coverage

- A skill MUST do one job that its name and description make obvious.
- Before adding a skill, check whether an existing skill can absorb the job. Prefer deleting
  or merging skills over adding new ones.
- Code and instructions MUST follow the `follow-the-rules` skill: simplify, delete what is
  unused, no restating comments, no "util" catch-alls.

Rationale: a registry of many overlapping skills triggers unreliably and costs context on
every session that loads it.

### V. Agent-Readable Instructions

Skills, agents, `AGENTS.md`, and `CLAUDE.md` are written for agents first.

- Edits to these files MUST follow the `writing-for-agents` guidance.
- A skill `description` MUST state when to trigger it in the words a user would actually say.
- Instructions MUST be imperative, specific, and free of facts that go stale quickly, such as
  deep file paths that are likely to move.
- Shared instructions live once in `AGENTS.md`; `CLAUDE.md` imports them with `@AGENTS.md`.

Rationale: description quality decides whether a skill triggers. Instruction quality decides
whether it works once triggered.

## Host Compatibility Constraints

- Plugin manifests for each host (`.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`)
  MUST carry the same plugin version.
- The plugin version follows semantic versioning: MAJOR for a removed or renamed skill or
  agent, or a breaking change in invocation; MINOR for a new skill or agent; PATCH for fixes
  and wording.
- The README host matrix MUST be updated in the same change that alters what a host receives.
- Skills MUST NOT depend on tools that only exist in the maintainer's local setup unless the
  skill degrades gracefully when the tool is absent.

## Development Workflow

- Work happens on a branch and lands on `main` through a pull request.
- Before merge: affected evals pass, plugin manifests agree on version, and the change has been
  reviewed against Principle I for leaked private information.
- Commit messages use Conventional Commits (`feat`, `fix`, `chore`, `docs`, ...).
- A version bump lands as its own `chore: bump plugin version to X.Y.Z` commit.
- Scratch output from experiments (`tmp/`, local caches) MUST stay out of version control.

## Governance

This constitution supersedes conflicting guidance elsewhere in the repository. `AGENTS.md`
holds runtime instructions for agents and MUST stay consistent with it.

- Amendments are made by pull request that edits this file and states the reason.
- Constitution versioning follows semantic versioning: MAJOR for removing or redefining a
  principle, MINOR for adding a principle or materially expanding guidance, PATCH for
  clarifications and wording.
- Every pull request review checks compliance with the Core Principles. A justified exception
  MUST be written in the PR description.

**Version**: 1.0.0 | **Ratified**: 2026-10-14 | **Last Amended**: 2026-10-14
