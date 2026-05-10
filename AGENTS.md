# AGENTS.md

General-purpose cross-tool skill pack for software engineering workflows.

## Critical Structure

- `skills/` - Agent skills with YAML frontmatter.
- `rules/` - Behavioral guidelines and repository conventions.
- `commands/` - Claude Code slash commands retained for Claude compatibility.
- `docs/agents/` - Setup docs used by the issue-tracker and domain-doc skills.

## Workflow

- **No Build**: Claude reads the repo root directly. Codex reads the in-repo plugin directory at `plugins/killall-skills`, which is wired to the root source files without copying. Restart or reinstall after local changes if the current session has stale plugin state.
- **Codex Testing**: Add the local marketplace with `codex plugin marketplace add /absolute/path/to/killall-skills`, then install `killall-skills` from the `killallgit` marketplace.
- **Claude Testing**: Add the local marketplace with `claude plugin marketplace add /absolute/path/to/killall-skills`, then install `killall-skills@killallgit`.
- **Cursor Testing**: Export the rule pack into a target repo with `bash scripts/export-cursor-rules.sh /path/to/project`.
- **Validation**: Run `bash scripts/smoke-test-install.sh` before release-worthy changes to plugin packaging or skill metadata.

## Release

- Keep `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` versions in sync.
- The version bump workflow updates both plugin manifests.
