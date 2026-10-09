# Structure tools

A structure tool owns how work is shaped in a repository: where specs, plans, issues, and docs live, and which skills write and review them. When one is in use, the factory defers to it and only runs lanes.

Facts below were checked against each project's README in October 2026. Confirm against the installed copy before you rely on a skill name; projects rename skills.

## Detect

| Tool | Signs it is installed |
| --- | --- |
| gstack (`garrytan/gstack`) | Skills named `gstack-*`, or `/review`, `/ship`, `/office-hours` from a `gstack` skills folder; `.gstack/` or `.gstack-worktrees/` in the repo; a gstack section in `CLAUDE.md` |
| mattpocock/skills | `to-spec`, `to-tickets`, `implement`, `tdd`, `triage`, `setup-matt-pocock-skills`; `.skill-lock.json` source `mattpocock/skills`; an `## Agent skills` block in `CLAUDE.md` or `AGENTS.md`; `docs/agents/` |
| agent-skills (`addyosmani/agent-skills`) | `spec-driven-development`, `planning-and-task-breakdown`, `incremental-implementation`, `code-review-and-quality`; plugin `agent-skills@addy-agent-skills` |
| Spec Kit (`github/spec-kit`) | `.specify/`, or skills and commands starting with `speckit` |

A process written into `AGENTS.md` or `CLAUDE.md` that names its own spec, issue, or review locations is a structure owner too, even with none of these tools.

## Per tool

### gstack

- Install: clone into `~/.claude/skills/gstack` and run `./setup`. Codex: `./setup --host codex`. Cursor: `./setup --host cursor` (experimental for both).
- Per-repo setup: optional. For a shared repo, `./setup --team` then `gstack-team-init required` vendors gstack into the repo; ask before doing this, since it commits `.claude/` changes.
- Spec: `/office-hours` or `/spec` (specs go to `$GSTACK_STATE_ROOT/projects/<slug>/specs/`); plan reviews: `/plan-eng-review`, `/autoplan`.
- Implement: no dedicated skill. Builders implement the approved spec.
- Review: `/review`, plus `/qa` or `/design-review` when the repo has a UI.
- Ship: `/ship` owns version, changelog, push, and PR. Integrate a lane through it only when the user asks to ship.
- Worktrees: gstack keeps its own under `.gstack-worktrees/`. Use that pattern for lanes when it exists.

### mattpocock/skills

- Install: `npx skills add mattpocock/skills`, which writes `.agents/skills/` and links each host.
- Per-repo setup: run `/setup-matt-pocock-skills`. It writes `docs/agents/issue-tracker.md`, `docs/agents/domain.md`, and the `## Agent skills` block. Every other skill in the set reads those files, so a repo without them is not set up.
- Spec: `to-spec`, then `to-tickets` to cut tickets. Issues live where `docs/agents/issue-tracker.md` says.
- Implement: `implement` or `implement-spec`, with `tdd`.
- Review: `code-review`.
- Domain docs: `CONTEXT.md` and `docs/adr/`, per `docs/agents/domain.md`.

### agent-skills

- Install: Claude Code `/plugin marketplace add addyosmani/agent-skills` then `/plugin install agent-skills@addy-agent-skills`. Codex: `codex plugin marketplace add addyosmani/agent-skills` then `codex plugin add agent-skills@agent-skills`. Any host: `npx skills add addyosmani/agent-skills`; a per-skill install drops the shared `references/`, so install the whole set.
- Per-repo setup: none for Claude Code or Codex. Cursor needs the skills copied into `.cursor/skills/`.
- Spec: `spec-driven-development` (`/spec`). Plan: `planning-and-task-breakdown` (`/plan`).
- Implement: `incremental-implementation` (`/build`), with `test-driven-development`.
- Review: `code-review-and-quality` (`/review`), plus `security-and-hardening`.
- Ship: `git-workflow-and-versioning`, `shipping-and-launch`.

### Spec Kit

- Install: `uvx --from git+https://github.com/github/spec-kit.git specify init --here`, choosing the host.
- Spec and plan: its specify, plan, and tasks steps write under `specs/<feature>/`.
- Implement: its implement step. Review: none built in; pair it with another tool's review skill or the factory reviewers.
