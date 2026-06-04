#!/usr/bin/env python3
"""voice-readback — speak an agent's reply aloud (ElevenLabs / OS TTS).

A *side-effect* hook (it plays audio); it does NOT follow the advisory
HOOK_INSTRUCTION model used by the phase hooks in this repo. It is registered
directly with a host's native turn-completion hook:

  Claude Code : Stop hook  -> `voice-readback.py --claude-stop`  (reads stdin JSON)
  Codex       : notify     -> `voice-readback.py --codex-notify` (JSON as last argv)

Runtime gate is in-chat and per "session":

  "speak to me"   -> replies after this are spoken
  "stop talking"  -> silent again

Off by default. Nothing is spoken until armed.

  Claude Code: state is derived from the transcript (scan your messages), so it
               is naturally per-session and needs no extra files to arm.
  Codex:       notify carries no message history, so enable/disable state is
               persisted in a small file keyed by the project `cwd`.

Config (env vars; a .env is also sourced, see resolve_env):
  ELEVENLABS_API_KEY   required for the elevenlabs provider
  TTMG_TTS             provider: "elevenlabs" (default if key) | "say" (OS voice)
  TTMG_VOICE_ID        ElevenLabs voice id   (default: Sarah)
  TTMG_MODEL           ElevenLabs model id   (default: eleven_flash_v2_5)
  TTMG_MAX_CHARS       cap spoken length     (default: 1500, 0 = no cap)
  TTMG_FALLBACK_SAY    "1" to fall back to OS voice if ElevenLabs fails (default 1)
  TTMG_ENV_FILE        explicit path to a .env to source vars from
"""

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

# --- defaults --------------------------------------------------------------
DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"   # Sarah (ElevenLabs stock voice)
DEFAULT_MODEL = "eleven_flash_v2_5"          # low-latency realtime model
DEFAULT_MAX_CHARS = 1500
OUTPUT_FORMAT = "mp3_44100_128"
VOICE_SETTINGS = {"stability": 0.5, "similarity_boost": 0.75}

ENABLE_RE = re.compile(r"\b(speak to me|talk to me|voice on|start speaking|read to me)\b", re.I)
DISABLE_RE = re.compile(r"\b(stop talking|stop speaking|be quiet|voice off|shut up)\b", re.I)
CMD_MAX_LEN = 40  # a phrase only counts as a command in a short message

STATE_DIR = os.path.expanduser("~/.cache/talk-to-me-goose")


# --- env / config ----------------------------------------------------------
def _parse_env_file(path):
    out = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip("\"'")
    except OSError:
        pass
    return out


def resolve_env():
    """A configured .env is the source of truth and overrides the process
    environment (so a stale/placeholder shell export can't shadow it); process
    env is the fallback for anything the .env doesn't define. Search order for
    the .env (first found wins): $TTMG_ENV_FILE, the repo root next to this
    hook, ~/.config/talk-to-me-goose/.env.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.environ.get("TTMG_ENV_FILE", ""),
        os.path.normpath(os.path.join(here, "..", "..", ".env")),  # killall-skills/.env
        os.path.expanduser("~/.config/talk-to-me-goose/.env"),
    ]
    file_vals = {}
    for path in candidates:
        if path and os.path.exists(path):
            for k, v in _parse_env_file(path).items():
                file_vals.setdefault(k, v)  # first .env found wins
    merged = dict(os.environ)   # base / fallback
    merged.update(file_vals)    # configured .env overrides process env
    return merged


ENV = resolve_env()


def env(key, default=""):
    return ENV.get(key, default)


# --- transcript / message parsing ------------------------------------------
def text_blocks(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content
                       if isinstance(b, dict) and b.get("type") == "text")
    return ""


def parse_transcript(path):
    """Return (human_texts_in_order, last_assistant_record) from a Claude Code jsonl."""
    humans, last_assistant = [], None
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("type") not in ("user", "assistant"):
                    continue
                txt = text_blocks((rec.get("message") or {}).get("content")).strip()
                if not txt:
                    continue  # skips tool_use / tool_result (no text block)
                if rec["type"] == "user":
                    humans.append(txt)
                else:
                    last_assistant = {"uuid": rec.get("uuid"), "text": txt}
    except OSError:
        pass
    return humans, last_assistant


def scan_state(human_texts, start=False):
    """Most recent trigger command wins. `start` is the prior state (for Codex,
    carried in a state file); Claude Code recomputes from scratch each time."""
    enabled = start
    for t in human_texts:
        if len(t.strip()) > CMD_MAX_LEN:
            continue
        if ENABLE_RE.search(t):
            enabled = True
        if DISABLE_RE.search(t):
            enabled = False
    return enabled


# --- text cleanup ----------------------------------------------------------
def clean_for_speech(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"[*_~>|#]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text).strip()
    cap = int(env("TTMG_MAX_CHARS", str(DEFAULT_MAX_CHARS)) or 0)
    if cap and len(text) > cap:
        text = text[:cap].rsplit(" ", 1)[0] + " ..."
    return text


# --- TTS providers ---------------------------------------------------------
def resolve_provider():
    p = env("TTMG_TTS", "").lower()
    if p in ("elevenlabs", "say"):
        return p
    return "elevenlabs" if env("ELEVENLABS_API_KEY") else "say"


def elevenlabs_tts(text):
    key = env("ELEVENLABS_API_KEY")
    if not key:
        return None
    voice = env("TTMG_VOICE_ID", DEFAULT_VOICE_ID)
    url = (f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
           f"?output_format={OUTPUT_FORMAT}")
    body = json.dumps({
        "text": text,
        "model_id": env("TTMG_MODEL", DEFAULT_MODEL),
        "voice_settings": VOICE_SETTINGS,
    }).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "xi-api-key": key, "content-type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except Exception:
        return None


def play_file(path):
    system = platform.system()
    if system == "Darwin" and shutil.which("afplay"):
        subprocess.run(["afplay", path], check=False)
        return True
    if system == "Windows":
        ps = (f"(New-Object Media.SoundPlayer '{path}').PlaySync();")
        # SoundPlayer is wav-only; use the shell association for mp3.
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Start-Process -Wait '{path}'"], check=False)
        return True
    for player, args in (("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet"]),
                         ("mpg123", ["-q"]), ("mpv", ["--really-quiet"]),
                         ("paplay", []), ("aplay", [])):
        if shutil.which(player):
            subprocess.run([player, *args, path], check=False)
            return True
    return False


def os_say(text):
    system = platform.system()
    if system == "Darwin" and shutil.which("say"):
        subprocess.run(["say", text], check=False)
        return True
    if system == "Windows":
        cmd = ("Add-Type -AssemblyName System.Speech; "
               "(New-Object System.Speech.Synthesis.SpeechSynthesizer)"
               f".Speak([Console]::In.ReadToEnd())")
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                       input=text, text=True, check=False)
        return True
    for cmd in (["spd-say", "-w"], ["espeak"]):
        if shutil.which(cmd[0]):
            subprocess.run([*cmd, text], check=False)
            return True
    return False


def synthesize_and_play(text):
    if not text:
        return
    provider = resolve_provider()
    if provider == "say":
        os_say(text)
        return
    audio = elevenlabs_tts(text)
    if audio is None:
        if env("TTMG_FALLBACK_SAY", "1") == "1":
            os_say(text)
        return
    fd, mp3 = tempfile.mkstemp(suffix=".mp3", prefix="ttmg-")
    with os.fdopen(fd, "wb") as f:
        f.write(audio)
    try:
        if not play_file(mp3) and env("TTMG_FALLBACK_SAY", "1") == "1":
            os_say(text)
    finally:
        try:
            os.remove(mp3)
        except OSError:
            pass


def speak_detached(text):
    """Re-invoke self as a worker so the hook returns immediately."""
    fd, txtfile = tempfile.mkstemp(suffix=".txt", prefix="ttmg-")
    with os.fdopen(fd, "w") as f:
        f.write(text)
    subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "--worker", txtfile],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )


# --- host entrypoints ------------------------------------------------------
def run_claude_stop(dry_run=False):
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    session_id = data.get("session_id", "default")
    humans, last_assistant = parse_transcript(data.get("transcript_path", ""))
    enabled = scan_state(humans, start=False)

    if dry_run:
        _emit_dry("claude-stop", enabled, last_assistant)
        return
    if not enabled or not last_assistant:
        return

    os.makedirs(STATE_DIR, exist_ok=True)
    state_file = os.path.join(STATE_DIR, f"spoken-{session_id}")
    last_spoken = _read(state_file)
    if last_assistant["uuid"] == last_spoken:
        return
    _write(state_file, last_assistant["uuid"] or "")
    speak_detached(clean_for_speech(last_assistant["text"]))


def run_codex_notify(argv, dry_run=False):
    # Codex passes the JSON payload as the LAST argument.
    raw = argv[-1] if argv else ""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return
    if data.get("type") != "agent-turn-complete":
        return
    cwd = data.get("cwd", "default")
    inputs = data.get("input-messages") or []
    reply = data.get("last-assistant-message") or ""

    os.makedirs(STATE_DIR, exist_ok=True)
    key = hashlib.sha1(cwd.encode()).hexdigest()[:16]
    state_file = os.path.join(STATE_DIR, f"codex-enabled-{key}")
    prior = _read(state_file) == "1"
    enabled = scan_state([str(m) for m in inputs], start=prior)

    if dry_run:
        _emit_dry("codex-notify", enabled, {"uuid": None, "text": reply})
        print(f"cwd={cwd} prior_enabled={prior}")
        return

    _write(state_file, "1" if enabled else "0")
    if enabled and reply:
        speak_detached(clean_for_speech(reply))


def _emit_dry(mode, enabled, last):
    print(f"mode={mode}")
    print(f"enabled={enabled}")
    print(f"provider={resolve_provider()}")
    if last and last.get("text"):
        print("would_speak=" + clean_for_speech(last["text"])[:200])


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


def _write(path, val):
    with open(path, "w") as f:
        f.write(val)


def main(argv):
    if len(argv) >= 2 and argv[0] == "--worker":
        # argv = ["--worker", txtfile]
        txtfile = argv[1]
        text = _read(txtfile)
        try:
            os.remove(txtfile)
        except OSError:
            pass
        synthesize_and_play(text)
        return

    dry = "--dry-run" in argv
    if "--codex-notify" in argv:
        run_codex_notify(argv, dry_run=dry)
    elif "--claude-stop" in argv:
        run_claude_stop(dry_run=dry)
    else:
        # default to Claude Code stdin mode
        run_claude_stop(dry_run=dry)


if __name__ == "__main__":
    main(sys.argv[1:])
