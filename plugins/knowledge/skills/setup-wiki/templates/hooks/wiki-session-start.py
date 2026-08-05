#!/usr/bin/env python3

import json
import sys
from pathlib import Path


MAX_CONTEXT_BYTES = 8192


def _load_payload():
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}


def _load_config(vault):
    try:
        return json.loads((vault / "wiki.json").read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def main():
    payload = _load_payload()
    if payload.get("hook_event_name") != "SessionStart":
        return 0
    cwd_value = payload.get("cwd")
    if not cwd_value:
        return 0
    vault = Path(__file__).resolve().parent.parent
    config = _load_config(vault)
    cwd = Path(cwd_value).expanduser().resolve()
    projects = [Path(value).expanduser().resolve() for value in config.get("projects", [])]
    if not any(_inside(cwd, project) for project in projects):
        return 0
    knowledge = vault / "KNOWLEDGE.md"
    if not knowledge.is_file():
        return 0
    context = knowledge.read_bytes()[:MAX_CONTEXT_BYTES].decode("utf-8", errors="ignore")
    sys.stdout.write(context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
