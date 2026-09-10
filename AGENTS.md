# AGENTS.md — distribution and host wiring

The repository distributes four domain bundles through the Codex marketplace
and individual skills through the cross-agent `skills` CLI. There is no bundled
installer. **Back up host config before editing it, preserve user-owned config,
and prefer host CLI commands over manual config changes.**

## What ships

- `GLOBAL_AGENT.md` — reusable baseline programming rules for global agent
  configuration.
- `.agents/plugins/marketplace.json` — the repo marketplace catalog.
- `plugins/<domain>/plugin.json` — the portable Agent Plugins manifest.
- `plugins/<domain>/.codex-plugin/plugin.json` — the Codex compatibility
  manifest and install-surface metadata.
- `plugins/<domain>/skills/<name>/SKILL.md` — the skill catalog, grouped into
  `planning`, `engineering`, `knowledge`, and `experimental` plugins.
- Companion scripts, templates, and references inside each skill directory.
- `agents/` — optional Claude Code subagents. Plugin and skill installation do
  not copy them.
- `hooks/voice-readback/` — a host-registered side-effect hook. Register it only
  on request.

## General install steps

1. Inspect the target host and determine whether the user requested a domain
   plugin or individual skills.
2. Check the CLI's current docs before changing config or hook wiring.
3. For Codex domain plugins, run
   `rtk codex plugin marketplace add killallgit/killall-skills` when the
   marketplace is not configured, then
   `rtk codex plugin add <domain>@killallgit`.
4. For individual skills, run
   `rtk npx skills@latest add killallgit/killall-skills --skill <name> --agent <host>`.
   Add `--global` for the user directory; omit it for the current project.
5. Copy subagents from `agents/` only when the user requests them.
6. Register hooks only when separately requested; installing a plugin or skill
   never implies hook registration.
7. Verify discovery and report exactly what was installed, removed, configured,
   skipped, or left for manual follow-up.

## Voice readback (`hooks/voice-readback/`) — optional, ask first

A side-effect hook that speaks the agent's reply aloud (ElevenLabs / OS voice).
It is **off until the user says "speak to me" in chat**, but registering it runs
the script on every turn-completion, so **only register it when the user opts in.**

Prerequisites:

- `python3` on PATH.
- A `.env` at the repo root (copy `.env.example`, set `ELEVENLABS_API_KEY`), or
  set `TTMG_TTS=say` to use the free OS voice with no key. The repo `.env` is
  authoritative and is gitignored.

Let `HOOK="$REPO/hooks/voice-readback/voice-readback.py"` (absolute path).

### Claude Code

Merge into the user's `settings.json` (`~/.claude/settings.json`, or the
project `.claude/settings.json` to scope to one repo). Back it up first.

- If `hooks.Stop` is absent, add it.
- If it exists, **append** a new entry to the `Stop` array — do not replace
  existing Stop hooks.

```json
{ "type": "command", "command": "python3 $HOOK --claude-stop", "timeout": 10 }
```

Hooks load at session start; tell the user to start a new session.

### Codex

Codex exposes a Stop hook that receives the same JSON payload shape on stdin:

```json
{ "type": "command", "command": "python3 $HOOK --codex-stop", "timeout": 10 }
```

Older Codex builds only support a **single** `notify` program in
`~/.codex/config.toml`:

```toml
notify = ["python3", "$HOOK", "--codex-notify"]
```

- If `notify` is absent, add the line above (back up the file first).
- If `notify` already exists, **stop and report** — do not overwrite it. Offer
  to write a small dispatcher that calls both the existing program and this hook,
  and point `notify` at the dispatcher.

### Verify (no audio)

```bash
rtk python3 "$HOOK" --codex-notify --dry-run \
  '{"type":"agent-turn-complete","cwd":"/x","input-messages":["speak to me"],"last-assistant-message":"ok"}'
# expect: enabled=True, provider=elevenlabs|say
```

### Uninstall

Remove the appended `Stop` entry from `settings.json` (leave other Stop hooks),
and remove or restore the `notify` line in `config.toml`. Optionally delete
`~/.cache/talk-to-me-goose/`.
