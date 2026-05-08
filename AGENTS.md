# AGENTS.md

General-purpose cross-tool skill pack for software engineering workflows.

## Critical Structure

- `skills/` - Agent skills with YAML frontmatter.
- `rules/` - Behavioral guidelines and repository conventions.
- `commands/` - Claude Code slash commands retained for Claude compatibility.
- `docs/agents/` - Setup docs used by the issue-tracker and domain-doc skills.

## Workflow

- **No Build**: Edits to Markdown skills take effect after reinstalling or restarting the agent session.
- **Codex Testing**: Add the local marketplace with `codex plugin marketplace add /absolute/path/to/killall-skills`, then install `killall-skills` from the `killallgit` marketplace.
- **Claude Testing**: Add the local marketplace with `claude plugin marketplace add /absolute/path/to/killall-skills`, then install `killall-skills@killallgit`.
- **Cursor Testing**: Export the rule pack into a target repo with `bash scripts/export-cursor-rules.sh /path/to/project`.
- **Validation**: Run `bash scripts/smoke-test-install.sh` before release-worthy changes to plugin packaging or skill metadata.

## Release

- Keep `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` versions in sync.
- The version bump workflow updates both plugin manifests.
