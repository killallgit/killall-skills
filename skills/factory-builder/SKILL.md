---
name: factory-builder
description: Install factory rails into a repository so its work runs as parallel sub-agents in isolated worktrees, following whatever structure tool the repository already uses, or remove them again.
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

## 2. Note the structure owner

A structure owner is whatever already decides how work is shaped here: where specs, plans, issues, and docs live, and which skills write, implement, and review them. The factory follows an owner when there is one. It installs nothing for structure, and it does not ask the user to pick one.

List every skill, hook, agent, and plugin that reaches this repository:

- Loaded in this session: the skills and agents in your context, and the plugins they come from.
- Project config: `.claude/settings.json` and `.claude/settings.local.json` (`hooks`, `enabledPlugins`, `skillOverrides`), `.claude/agents/`, `.claude/skills/`, `.agents/skills/`, `.cursor/`, `.codex/config.toml`.
- Process instructions in `AGENTS.md`, `CLAUDE.md`, and the files they import: spec-driven development, ADRs, and where docs, specs, and issues are stored.

An owner covers specs and at least one of implement or review. The evidence is skills whose descriptions say they write specs, plans, or tickets, implement a spec, or review a diff; per-repo files those skills wrote, such as a spec directory, an issue-tracker doc, or domain docs; or a process written into the instruction files.

- **One obvious owner**: record its name and, for each of spec, implement, and review, the skill that fills it and where its artifacts live.
- **Several candidates**: the one with per-repo files in this repository is the owner. When none or several have them, treat it as no owner.
- **No owner**: record `factory` and what you found. The factory's own loop shapes the work.

When the user has said a tool or plugin stays out of this project, disable it for each host the user names. Follow [references/disable-plugins-and-skills.md](references/disable-plugins-and-skills.md) and write to that host's local, uncommitted settings unless the user asks for a team-wide change. Record each one as a `change` and the `revert` that undoes it, including the value the setting had before. These go into the `setup` field in step 7.

Done when the owner, or `factory`, is recorded with its evidence, and every exclusion the user named is disabled and recorded.

## 3. Check the owner's skills

Skip this step when the owner is `factory`.

Resolve each skill recorded in step 2 on each host: Claude Code reads `.claude/skills/` and `~/.claude/skills/` plus enabled plugins, Codex reads `.agents/skills/` and `~/.agents/skills/` plus enabled plugins, and Cursor reads `.cursor/skills/`, `.agents/skills/`, `.claude/skills/`, and `.codex/skills/`, plus the same folders under `~`. Each `SKILL.md` has frontmatter whose `name` matches its folder.

A skill that does not resolve on a host stays out of that slot; the slot takes its fallback sentence in step 5. When the owner expects per-repo setup that is missing, note it for the report. Install nothing and run no setup.

Done when each slot names a skill that resolves on every host, or is marked for its fallback.

## 4. Read git and worktree rules

Read the instruction files, the git hooks (`.husky/`, `.pre-commit-config.yaml`, `lefthook.yml`, `git config core.hooksPath`), any session hook that blocks git commands, and the owner's own worktree convention. Run `git worktree list` to see where existing worktrees live. Record:

- The worktree pattern: where a worktree lives, and the command that creates and removes one.
- Branch naming, commit message format, merge or rebase policy, and push or pull-request rules.

Compare them with the factory defaults: branches named `factory/<id>`, a fast-forward merge onto the default branch, push only on request, and a one-sentence plain commit message. When a rule conflicts with a default, ask the user which side wins.

When a host runs a `serena` MCP server, or `.serena/project.yml` exists, follow [references/serena.md](references/serena.md).

Done when every rule is recorded, every conflict has an answer, and the Serena check is recorded when it applies.

## 5. Inspect

Record these, from the repo rather than from memory:

| Field | Where it comes from |
| --- | --- |
| `project` | One sentence: what this repo is |
| `structure` | The owner's name from step 2, or `factory` for the factory's own loop |
| `default_branch` | `origin/HEAD`, else the branch the user names |
| `conventions` | The instruction file that holds this repo's rules, such as `` `AGENTS.md` `` or `` `CLAUDE.md` ``; otherwise `the patterns already in the code` |
| `gate` | The one command that must pass before work lands |
| `gate_scopes` | Optional. One sentence naming a smaller check per area when the repo defines one, such as a per-package test command; empty otherwise |
| `spec_tool` | The spec paragraph below |
| `implement_tool` | The implement paragraph below |
| `review_tool` | The review paragraph below |
| `isolation_note` | The git and worktree note below, plus the Serena sentence when step 4 found Serena |
| `lenses` | Own loop only: `code` and `security`, plus `ux` and `design` when the repo has a user interface |

Gate, in order: the check a pull-request workflow actually runs; otherwise one of `task check`, `make check`, `just check`, `npm test`, `pnpm test`, `cargo test`, `go test ./...`, `pytest`. Ask when two of these are equally plausible. Done for this field when one command is chosen.

### Tool paragraphs

Each paragraph names a skill that resolved in step 3, and where its artifact lives. A slot marked for its fallback in step 3 uses the fallback sentence.

With a structure tool as owner:

- `spec_tool`: "Shape the work with `<skill>`. It writes the spec to `<place>`. Read the spec from there and leave it there." When the spec skill did not resolve: "Write the spec from the feature request and the code, and store it where the owner keeps specs."
- `implement_tool`: "Implement with `<skill>`." When the owner has no implement skill: "Make the change yourself against the spec."
- `review_tool`: "Review with `<skill>`." When the owner has no review skill: "Review the diff against the spec's acceptance checks."

With the factory's own loop, the factory's Output shapes are the contract and the agents file their artifacts under `.factory/jobs/`:

- `spec_tool`: "Write the spec from the feature request and the code. Ground every acceptance check in a file or behavior you found."
- `implement_tool`: "Make the change yourself against the spec."
- `review_tool`: "Review the diff against the spec."

Another installed skill that fills one slot, such as a test-first skill for implementation, adds one sentence naming it to that paragraph.

### Git and worktree note

`isolation_note` is the rules from step 4, as instructions to a builder:

1. The worktree: "Worktrees are created with `<command>` at `<location>`. Before the first edit, confirm you are on the branch the brief names, in the worktree it names." When step 4 found no pattern, use "Worktrees follow this repository's existing pattern." for the first sentence.
2. The commit format: the confirmed rule, or "Each commit message is one plain sentence."
3. Each other confirmed git rule, one sentence each, including any repository rule the user chose over a factory default.

When step 4 found Serena, append the sentence from [references/serena.md](references/serena.md).

### Lenses

Own loop only. Lenses are only `code`, `security`, `ux`, and `design`. Add `ux` and `design` when the repo ships a user interface. A new lens means a new section in `templates/reviewer.tmpl.md` first.

Done when every field above is written down, each tool paragraph names a skill that resolved in step 3 or is a fallback sentence, and `isolation_note` carries every confirmed git rule.

## 6. Confirm a refresh

Look for `.factory/board.json` or a factory agent symlink under `.claude/agents/` from a previous install.

Fresh repository: the user's invocation is the request. Continue.

Factory already present: summarize what a refresh will overwrite and wait for a yes. When the owner changed, the previous install's agents and symlinks that the new install set lacks stay behind; list them in that summary and remove them after the yes. Done when this is a fresh install, or the user told you to refresh.

## 7. Render

Write the fields to a temporary JSON file. `lenses` is an array of strings, and only the own loop needs it. `setup` is the array of `{"change", "revert"}` objects from step 2. Do not put that file in the repository.

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
- The owner and the evidence for it, or that there was none.
- Any slot left on its fallback, and any per-repo setup the owner expects that is missing.
- Every tool disabled in step 2, and the settings file it went into.
- Where specs, docs, and issues are stored.
- The git rules in `isolation_note`.
- The Serena findings, when step 4 found Serena.
- The first command: `/factory` plus a spec, plan, ticket list, or feature (`$factory` in Codex). With the own loop, also `/factory next`.
- Codex loads the agents in `.codex/agents/` only when this project is trusted in `~/.codex/config.toml`.
- `python3 -m http.server` run from `.factory/` serves the board.
- `/factory-builder uninstall` (`$factory-builder uninstall` in Codex) takes all of it out again.

The factory is installed. Do not start a job in this same turn unless the user asked for one.
