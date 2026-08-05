# voice-readback

Speak an agent's reply aloud when a turn completes — ElevenLabs by default, OS
voice as a free fallback. Works in **Claude Code** and **Codex**.

This is a **host-registered side-effect hook**: it plays audio and is wired
directly into a host's native turn-completion hook. It does *not* follow the
advisory `HOOK_INSTRUCTION:` / phase model used by the other hooks in this repo
(see `../README.md`), and it is written in Python rather than Bash because it
parses transcript JSON, scans for trigger phrases, and cleans markdown.

## Runtime toggle (off by default)

Nothing is spoken until you arm it, in chat:

- **"speak to me"** → replies after this are spoken
- **"stop talking"** → silent again

(Also: `talk to me` / `voice on` / `start speaking` / `read to me`, and
`stop speaking` / `be quiet` / `voice off`. A phrase only counts as a command in
a short message, so discussing the feature doesn't arm it.)

How the on/off state is tracked differs by host:

- **Claude Code** — derived from the transcript (your messages are scanned every
  turn). Naturally per-session; no state file needed.
- **Codex** — the `notify` payload carries no message history, so enabled/disabled
  state is persisted in `~/.cache/talk-to-me-goose/codex-enabled-<cwd-hash>`,
  keyed by the project directory. Voice is therefore on/off **per project dir**
  for Codex, toggled by saying the phrase in that directory.

## Configuration

Read from the environment; a `.env` (repo root, `~/.config/talk-to-me-goose/.env`,
or `$TTMG_ENV_FILE`) is **authoritative and overrides shell variables**. See
`.env.example` at the repo root.

| Var | Default | Meaning |
|---|---|---|
| `ELEVENLABS_API_KEY` | — | ElevenLabs key (`sk_…`). Blank → OS voice. |
| `TTMG_TTS` | `elevenlabs` if key else `say` | Provider: `elevenlabs` or `say` (OS voice). |
| `TTMG_VOICE_ID` | `EXAVITQu4vr4xnSDxMaL` (Sarah) | ElevenLabs voice id. |
| `TTMG_MODEL` | `eleven_flash_v2_5` | ElevenLabs model (low-latency). |
| `TTMG_MAX_CHARS` | `1500` | Cap spoken length (0 = no cap). |
| `TTMG_FALLBACK_SAY` | `1` | Fall back to OS voice if ElevenLabs fails. |

Playback auto-detects: `afplay` (macOS), `ffplay`/`mpg123`/`mpv`/`paplay`/`aplay`
(Linux), PowerShell (Windows). OS voice uses `say` / `spd-say`/`espeak` /
System.Speech.

## Registration

Register the hook manually after opting in (see the repo `AGENTS.md`):

### Claude Code — `Stop` hook in `settings.json`

```json
{
  "hooks": {
    "Stop": [
      { "hooks": [
        { "type": "command",
          "command": "python3 /ABS/PATH/killall-skills/hooks/voice-readback/voice-readback.py --claude-stop",
          "timeout": 10 }
      ] }
    ]
  }
}
```

The hook reads the Stop payload (`session_id`, `transcript_path`) on stdin.

### Codex — `notify` in `~/.codex/config.toml`

```toml
notify = ["python3", "/ABS/PATH/killall-skills/hooks/voice-readback/voice-readback.py", "--codex-notify"]
```

Codex appends the `agent-turn-complete` JSON payload as the last argument.

> **Codex allows only one `notify` program.** If you already have a `notify`
> configured, you must chain them (point `notify` at a small dispatcher that
> calls both) rather than overwrite it. Stop when an existing program is present
> rather than clobber an existing `notify`.

## Testing without audio

```bash
# Claude Code mode
printf '{"session_id":"s","transcript_path":"/path/to/transcript.jsonl"}' \
  | python3 voice-readback.py --claude-stop --dry-run

# Codex mode
python3 voice-readback.py --codex-notify --dry-run \
  '{"type":"agent-turn-complete","cwd":"/proj","input-messages":["speak to me"],"last-assistant-message":"Hi."}'
```

Prints the resolved `enabled` state, `provider`, and a preview of what would be
spoken. Never calls the TTS API or plays audio.
