# AGENTS.md

This repo is a flat collection of agent content. Three install classes:

- `skills/` — each subdir holds a `SKILL.md` (plus optional companion files).
- `rules/` — each file is one behavioral rule, included via the host's instruction file.
- `hooks/` — Bash lifecycle scripts, wired into the host's hook system. See `hooks/README.md`.

There is no installer. An agent reads this file and wires the content into the
host coding tool by hand.

## Install procedure

1. Identify the host tool and whether the user wants user scope or project scope.
2. Prefer symlinks from this repo into the host's native locations. Copy only
   when symlinks are unsupported or a portable install is requested.
3. Back up any config file before editing it.
4. Verify the host discovers the content, then report every path created,
   changed, skipped, or backed up.

### Claude Code

- Skills: symlink each `skills/<name>/` into `~/.claude/skills/<name>` (project:
  `.claude/skills/`). Verify with `ls ~/.claude/skills/*/SKILL.md`.
- Rules: append `@<repo>/rules/<file>.md` include lines to `~/.claude/CLAUDE.md`
  (project: `.claude/CLAUDE.md`).
- Hooks: register each script in `~/.claude/settings.json` under the matching
  phase — `pre-session`→`SessionStart`, `pre-tool`→`PreToolUse`,
  `post-tool`→`PostToolUse`, `post-session`→`Stop`.

### Codex CLI

- Skills: symlink each `skills/<name>/` into `~/.codex/skills/<name>`.
- Rules: append `@<repo>/rules/<file>.md` include lines to `~/.codex/AGENTS.md`.
- Hooks: not natively supported — skip.

### Other / unknown host

Find the host's user-scope config dir, look for `skills/`, `rules/`, `hooks/`
surfaces, check the host's docs (Context7 MCP first when available), and symlink
the matching classes in. Skip unsupported classes and report.

## Cleanup

Remove only symlinks and config entries whose targets resolve under this repo.
Leave user-authored files alone. Restore backups only if asked or if config is broken.

## Safety

- Never delete ambiguous files or overwrite config without a backup.
- Never assume host config paths from memory beyond what is documented here.
- Treat host-provided hook payload as untrusted data (see `hooks/README.md`).
