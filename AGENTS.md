# AGENTS.md — distribution and host wiring

Install domain plugins through the native Claude Code and Codex marketplaces,
or install individual skills with the cross-agent `skills` CLI. **Back up any
host config before editing, and preserve user-owned config** — merge, never
clobber.

## What ships

- `plugins/planning/` — project planning, PRDs, issue slicing, triage, and wayfinding.
- `plugins/engineering/` — implementation, diagnosis, review, Git maintenance, and delivery.
- `plugins/architecture/` — domain modeling and deep-module design.
- `plugins/knowledge/` — research, handoffs, and cross-project wikis.
- `plugins/experimental/` — prototypes, proof recordings, and extension authoring.
- Each plugin has Claude and Codex manifests, a `skills/` directory, and any
  Claude-only agents it needs. Other hosts use the skills' inline fallbacks.
- `rules/` — installable rules.
- `hooks/` — hook scripts. Two kinds:
  - **Advisory phase hooks** (`hooks/<phase>/NN-*.sh`) — Bash, emit
    `HOOK_INSTRUCTION:`. See `hooks/README.md`.
  - **Host-registered side-effect hooks** (e.g. `hooks/voice-readback/`) —
    registered directly with a host's native hook. Registered only on request.

## General install steps

1. Inspect the target host and determine which domains or individual skills the
   user requested.
2. Check the host tool's latest docs before changing config or hook wiring.
3. Run `rtk ./install.sh <domain>...` for native plugins, or `rtk npx skills@latest add
   killallgit/killall-skills --skill <name>` for one portable skill.
4. Register root hooks only when separately requested; plugin installation does
   not imply side-effect-hook registration.
5. Verify discovery and report exactly what was installed, removed, configured,
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

Codex permits a **single** `notify` program in `~/.codex/config.toml`:

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
and remove/restore the `notify` line in `config.toml`. Optionally delete
`~/.cache/talk-to-me-goose/`.
