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

## Install — Claude Code

```bash
claude plugin marketplace add killallgit/killall-skills
claude plugin install killall-skills@killallgit
```

## Install — Codex

```bash
codex plugin marketplace add killallgit/killall-skills
```

## Local development

```bash
claude --plugin-dir ~/Code/killallgit/killall-skills
```
