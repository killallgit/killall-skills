# AGENTS.md

General-purpose Codex plugin for software engineering skills.

## Critical Structure

- `skills/` - Agent skills with YAML frontmatter.
- `rules/` - Behavioral guidelines and repository conventions.
- `commands/` - Claude Code slash commands retained for Claude compatibility.
- `docs/agents/` - Setup docs used by the issue-tracker and domain-doc skills.

## Workflow

- **No Build**: Edits to Markdown skills take effect after reinstalling or restarting the agent session.
- **Codex Testing**: Add the local marketplace with `codex plugin marketplace add ~/Code/killallgit/killall-skills`, then install `killall-skills` from `/plugins`.
- **Claude Testing**: Install the local plugin path with `/plugin install .` from the repo root.

## Release

- Keep `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` versions in sync.
- The version bump workflow updates both plugin manifests.
