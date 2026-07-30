# killall-skills

Engineering workflow skills — project scoping, planning
(brief -> PRD -> issues -> TDD), cross-project knowledge wikis, triage,
diagnostics, and tooling — for Claude Code and Codex.

## What ships

- `payload/skills/` — installable skills, including project-planner, the
  PRD/issues/TDD workflow, and generic cross-project wiki setup and maintenance.
- `payload/agents/` — Claude Code subagents, including project-planner and
  git-janitor helpers.
- `rules/` and root `hooks/` — installable repo rules and optional host hooks.

## Install

```bash
git clone https://github.com/killallgit/killall-skills
cd killall-skills
./install.sh
```

The installer idempotently installs or refreshes the plugin in every supported
host found on `PATH`. Re-run it after `git pull`, or use `./install.sh --remove`
to uninstall it. Restart Claude Code and Codex after either operation.

<details>
<summary>Manual install</summary>

```bash
# Claude Code
claude plugin marketplace add killallgit/killall-skills
claude plugin install killall-skills@killallgit

# Codex
codex plugin marketplace add killallgit/killall-skills
codex plugin add killall-skills@killallgit
```

</details>

## Local development

```bash
claude --plugin-dir ~/Code/killallgit/killall-skills
```
