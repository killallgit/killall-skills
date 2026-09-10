# Wiki Hook Integration

Hooks are optional. The vault works without them. Register only the hosts and
config paths the user confirmed.

The vault-local scripts share one contract:

- `hooks/wiki-session-start.py` injects at most 8 KiB of `KNOWLEDGE.md` when
  the session cwd is inside a configured project.
- `hooks/wiki-session-end.py` creates a metadata-only review candidate when a
  scoped Git project is dirty. It never copies transcript text or filenames.

## Install

Run the companion installer with absolute paths:

```bash
python3 <skill-dir>/scripts/install-wiki-hooks.py \
  --host codex \
  --vault <absolute-vault-path>
```

Use `--host claude` for Claude Code. Use `--config <path>` only when the user
selected a non-default config.

Defaults:

- Claude Code: `~/.claude/settings.json`
- Codex: `~/.codex/hooks.json`

The installer adds `SessionStart` and `SessionEnd`, preserves unrelated hooks,
backs up changed config, and is idempotent. Invalid JSON stops before backup or
write.

Codex hooks are enabled by default. Do not add `codex_hooks`; it is a deprecated
alias. Codex requires review and trust when a command hook's definition changes.
Claude Code loads user settings on the next session.

Current schemas:

- [Claude Code hooks](https://code.claude.com/docs/en/hooks)
- [Codex hooks](https://developers.openai.com/codex/hooks/)

## Verify

Run setup against temporary config paths first when changing installer
behavior. For a real install:

1. Parse the resulting JSON.
2. Confirm unrelated events and handlers remain.
3. Start a session inside one configured project and confirm bounded context.
4. Start outside scope and confirm silence.
5. End a dirty scoped session and inspect the metadata-only candidate in
   `queues/review/`.

## Remove

```bash
python3 <skill-dir>/scripts/install-wiki-hooks.py \
  --host codex \
  --vault <absolute-vault-path> \
  --remove
```

Removal deletes only handlers pointing to that vault and creates a backup when
the config changes.
