#!/usr/bin/env python3

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


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


def _scoped_project(cwd, projects):
    for project in projects:
        try:
            cwd.relative_to(project)
            return project
        except ValueError:
            continue
    return None


def _dirty_count(project):
    try:
        result = subprocess.run(
            ["git", "-C", str(project), "status", "--porcelain", "--untracked-files=all"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 0
    if result.returncode != 0:
        return 0
    return len([line for line in result.stdout.splitlines() if line.strip()])


def _write_candidate(vault, payload, cwd, dirty_count):
    session_id = str(payload.get("session_id") or "unknown-session")
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:16]
    target = vault / "queues" / "review" / f"session-{digest}.json"
    if target.exists():
        return
    candidate = {
        "type": "session_review",
        "status": "candidate",
        "session_id": session_id,
        "cwd": str(cwd),
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "dirty_file_count": dirty_count,
        "reason": str(payload.get("reason") or "other"),
    }
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def main():
    payload = _load_payload()
    if payload.get("hook_event_name") != "SessionEnd":
        return 0
    cwd_value = payload.get("cwd")
    if not cwd_value:
        return 0
    vault = Path(__file__).resolve().parent.parent
    config = _load_config(vault)
    cwd = Path(cwd_value).expanduser().resolve()
    projects = [Path(value).expanduser().resolve() for value in config.get("projects", [])]
    project = _scoped_project(cwd, projects)
    if project is None:
        return 0
    dirty_count = _dirty_count(project)
    if dirty_count:
        _write_candidate(vault, payload, cwd, dirty_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
