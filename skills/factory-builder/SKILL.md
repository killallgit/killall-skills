---
name: factory-builder
description: Install factory rails into a repository so its work runs as parallel sub-agents in isolated worktrees, on top of whatever structure tool the repository uses, with that tool's skills set up for every host.
disable-model-invocation: true
argument-hint: "[uninstall|remove] [path]"
---

# Factory builder

Install a factory into a repository. A factory is rails, not a process: it runs work as parallel sub-agent lanes, each in its own worktree, and verifies every lane before it lands. How work is shaped belongs to the repository's structure owner, such as gstack, mattpocock/skills, agent-skills, or Spec Kit. The factory ships its own spec, review, and approve loop only for a repository without one.

This skill is the builder. Factory jobs run later, in that repository, under `/factory` (`$factory` in Codex).

When the first argument is `uninstall` or `remove`, follow [references/uninstall.md](references/uninstall.md) instead of the steps below. Everything an install adds is recorded so that an uninstall can take it out.

The install set is generated from `templates/`. `agents/openai.yaml` next to this file keeps Codex from invoking this skill on its own. Coordination rules live in `templates/orchestrator.tmpl.md`, which is filled with the gate, conventions, and git rules this repository actually has.

## What gets written

Factory state lives in `.factory/` and is not committed. The install adds two tracked lines so that state still exists for every checkout:

- `.gitignore` lists `.factory/`
- `.worktreeinclude` lists `.factory/`, so tools that copy gitignored files into a new worktree bring this directory along

`.factory/` holds `board.json`, `backlog.md`, `dashboard.html`, `manifest.json`, and the rendered agents. `manifest.json` records every file, link, line, and setup change the install made. Each agent is written once under `.factory/agents/<host>/` and symlinked into the directory that host reads:

- `.factory/agents/claude/<name>.md` → `.claude/agents/<name>.md`
- `.factory/agents/cursor/<name>.md` → `.cursor/agents/<name>.md`
- `.factory/agents/codex/<name>.toml` → `.codex/agents/<name>.toml`

The symlink is what the host loads. Editing the file under `.factory/agents/` updates that host.

Which agents and which `/factory` skill get installed depends on the owner:

| Owner | Agents | `/factory` skill |
| --- | --- | --- |
| A structure tool | `orchestrator`, `builder` | `templates/factory-rails.tmpl.md`: lanes built from the owner's spec, reviewed with the owner's review skill |
| The factory's own loop | `orchestrator`, `builder`, `spec-writer`, `review-<lens>`, `approver` | `templates/factory.tmpl.md`: spec, build, review, approve |

The `/factory` skill is written to `.agents/skills/factory/SKILL.md`, `.claude/skills/factory/SKILL.md`, and `.cursor/skills/factory/SKILL.md`. Those three copies are the same bytes. Change the factory by editing the template and rendering again.

## 1. Name the repository

Use the path the user gave, otherwise the current git root.

```bash
git rev-parse --show-toplevel
```

Done when that path is the repository you will write into.

## 2. Find the structure owner

A structure owner decides how work is shaped here: where specs, plans, issues, and docs live, and which skills write and review them. The factory follows the owner. It adds nothing the owner already does.

List every skill, hook, agent, and plugin that reaches this repository:

- Loaded in this session: the skills and agents in your context, and the plugins they come from.
- Project config: `.claude/settings.json` and `.claude/settings.local.json` (`hooks`, `enabledPlugins`, `skillOverrides`), `.claude/agents/`, `.claude/skills/`, `.agents/skills/`, `.cursor/`, `.codex/config.toml`, `.specify/`.
- Process instructions in `AGENTS.md`, `CLAUDE.md`, and the files they import: spec-driven development, ADRs, and where docs, specs, and issues are stored.

Match what you found against [references/structure-tools.md](references/structure-tools.md).

- **One clear owner**: name it, show the evidence, and ask the user to confirm it.
- **Several, or none**: ask the user to choose. Offer each tool you found, then gstack, mattpocock/skills, and agent-skills, then the factory's own loop. The factory's own loop is the spec-writer, builder, reviewers, and approver this skill ships.

In the same message, list the other tools you found and ask which stay out of this project. A second structure tool whose skills fire on their own competes with the owner; name it as a candidate to disable.

Done when the user has named the owner and every tool to exclude.

## 3. Set up the skills

The factory only names skills it has seen on disk for every host this repository supports.

1. Install the owner when it is missing, using its install line in the reference. Ask before an install that writes outside this repository.
2. Run the owner's per-repo setup from the reference. When the owner has a setup skill, follow that skill; it asks its own questions.
3. Disable each excluded tool for each host. Follow [references/disable-plugins-and-skills.md](references/disable-plugins-and-skills.md) and write to that host's local, uncommitted settings unless the user asks for a team-wide change.
4. Resolve the owner's spec, implement, and review skills on each host: Claude Code reads `.claude/skills/` and `~/.claude/skills/` plus enabled plugins, Codex reads `.agents/skills/` and `~/.agents/skills/` plus enabled plugins, and Cursor reads `.cursor/skills/`, `.agents/skills/`, `.claude/skills/`, and `.codex/skills/`, plus the same folders under `~`. Each `SKILL.md` has frontmatter whose `name` matches its folder.

Record every change this step makes, as a `change` and the `revert` that undoes it, including the value a setting had before. Installs, setup-skill output, and settings edits all count. These go into the `setup` field in step 7.

Skip this step when the owner is the factory's own loop, apart from the exclusions.

Done when every stage skill the factory will name resolves to a `SKILL.md` on every host, and every excluded tool is disabled.

## 4. Read git and worktree rules

Read the instruction files, the git hooks (`.husky/`, `.pre-commit-config.yaml`, `lefthook.yml`, `git config core.hooksPath`), any session hook that blocks git commands, and the owner's own worktree convention. Run `git worktree list` to see where existing worktrees live. Record:

- The worktree pattern: where a worktree lives, and the command that creates and removes one.
- Branch naming, commit message format, merge or rebase policy, and push or pull-request rules.

Compare them with the factory defaults: branches named `factory/<id>`, a fast-forward merge onto the default branch, push only on request, and a one-sentence plain commit message. When a rule conflicts with a default, ask the user which side wins.

Done when every rule is recorded and every conflict has an answer.

## 5. Inspect

Record these, from the repo rather than from memory:

| Field | Where it comes from |
| --- | --- |
| `project` | One sentence: what this repo is |
| `structure` | The owner's name from step 2, or `factory` for the factory's own loop |
| `default_branch` | `origin/HEAD`, else the branch the user names |
| `conventions` | `` `AGENTS.md` `` when that file exists, otherwise `the patterns already in the code` |
| `gate` | The one command that must pass before work lands |
| `spec_tool` | The spec paragraph below |
| `implement_tool` | The implement paragraph below |
| `review_tool` | The review paragraph below |
| `isolation_note` | The git and worktree note below, plus the Serena paragraph when Serena is configured |
| `lenses` | Own loop only: `code` and `security`, plus `ux` and `design` when the repo has a user interface |

Gate, in order: the check a pull-request workflow actually runs; otherwise one of `task check`, `make check`, `just check`, `npm test`, `pnpm test`, `cargo test`, `go test ./...`, `pytest`. Ask when two of these are equally plausible. Done for this field when one command is chosen.

### Tool paragraphs

Each paragraph names a skill that resolved in step 3, and where its artifact lives.

With a structure tool as owner:

- `spec_tool`: "Shape the work with `<skill>`. It writes the spec to `<place>`. Read the spec from there and leave it there."
- `implement_tool`: "Implement with `<skill>`." When the owner has no implement skill: "Make the change yourself against the spec."
- `review_tool`: "Review with `<skill>`." When the owner has no review skill: "Review the diff against the spec's acceptance checks."

With the factory's own loop, the factory's Output shapes are the contract and the agents file their artifacts under `.factory/jobs/`:

- `spec_tool`: "Write the spec from the feature request and the code. Ground every acceptance check in a file or behavior you found."
- `implement_tool`: "Make the change yourself against the spec."
- `review_tool`: "Review the diff against the spec."

A tool the user kept that fills one slot, such as `tdd` for implementation, adds one sentence naming it to that paragraph.

### Git and worktree note

`isolation_note` is the rules from step 4, as instructions to a builder:

1. The worktree: "Create the worktree for the branch the brief names with `<command>`, at `<location>`. Before the first edit, confirm you are on that branch in that checkout." When step 4 found no pattern, use "Use this repository's existing worktree pattern for the branch the brief names." for the first sentence.
2. The commit format: the confirmed rule, or "Each commit message is one plain sentence."
3. Each other confirmed git rule, one sentence each, including any repository rule the user chose over a factory default.

When `.serena/project.yml` exists, append: "Serena binds its project root when its process starts. If your process started in the primary checkout, Serena reads and writes that checkout even while your other tools point at the worktree. Use the worktree's files through the editor tools, and leave Serena unused."

### Lenses

Own loop only. Lenses are only `code`, `security`, `ux`, and `design`. Add `ux` and `design` when the repo ships a user interface. A new lens means a new section in `templates/reviewer.tmpl.md` first.

Done when every field above is written down, each tool paragraph names a skill that resolved in step 3 or is a fallback sentence, and `isolation_note` carries every confirmed git rule.

## 6. Confirm a refresh

Look for `.factory/board.json` or a factory agent symlink under `.claude/agents/` from a previous install.

Fresh repository: the user's invocation is the request. Continue.

Factory already present: summarize what a refresh will overwrite and wait for a yes. When the owner changed, the previous install's agents and symlinks that the new install set lacks stay behind; list them in that summary and remove them after the yes. Done when this is a fresh install, or the user told you to refresh.

## 7. Render

Write the fields to a temporary JSON file. `lenses` is an array of strings, and only the own loop needs it. `setup` is the array of `{"change", "revert"}` objects from step 3. Do not put that file in the repository.

From this skill's directory:

```bash
python3 scripts/render_factory.py --dest <git-root> --vars <temp.json>
```

On a confirmed refresh, add `--force`.

The script picks the install set from `structure`, then writes `.factory/`, the gitignore line, the `.worktreeinclude` line, the agent symlinks, and `.factory/manifest.json`. It skips existing files unless `--force`, and exits non-zero if a `{{token}}` is left or a lens is unknown.

Done when the script exits 0 and every generated agent and skill file is free of `{{`.

## 8. Report

Tell the user:

- The git root, the owner, and the gate.
- Each stage skill the factory names, and the hosts it resolved on.
- Every tool disabled in step 2, and the settings file it went into.
- Where specs, docs, and issues are stored.
- The git rules in `isolation_note`.
- The first command: `/factory` plus a spec, plan, ticket list, or feature (`$factory` in Codex). With the own loop, also `/factory next`.
- Codex loads the agents in `.codex/agents/` only when this project is trusted in `~/.codex/config.toml`.
- `python3 -m http.server` run from `.factory/` serves the board.
- `/factory-builder uninstall` (`$factory-builder uninstall` in Codex) takes all of it out again.

The factory is installed. Do not start a job in this same turn unless the user asked for one.
