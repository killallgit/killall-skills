#!/usr/bin/env python3
"""Build a throwaway git repository for agent-setup evals."""

from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

SKILL_PATH = "skills/agent-setup"
LEGACY_VARS = Path(__file__).resolve().parent / "vars-legacy.json"


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def write_files(repo: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def extract_skill(ref: str, dest: Path) -> Path:
    """Unpack skills/agent-setup as it was at `ref` and return its folder."""
    top = git(Path(__file__).resolve().parent, "rev-parse", "--show-toplevel")
    dest.mkdir(parents=True, exist_ok=True)
    archive = dest / "skill.tar"
    with archive.open("wb") as handle:
        subprocess.run(["git", "-C", top, "archive", ref, SKILL_PATH], stdout=handle, check=True)
    with tarfile.open(archive) as tar:
        tar.extractall(dest)
    return dest / SKILL_PATH


def set_up_with(ref: str, repo: Path, vars_path: Path, hosts: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        skill = extract_skill(ref, Path(tmp))
        subprocess.run(
            [sys.executable, str(skill / "scripts/render_agents.py"), "--dest", str(repo),
             "--vars", str(vars_path), "--hosts", hosts],
            check=True,
            capture_output=True,
        )


def build(repo: Path, files: dict[str, str], previous: dict[str, str] | None = None) -> Path:
    """Create `repo` with `files` committed, then optionally run an earlier agent-setup over it."""
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    git(repo, "config", "user.name", "Fixture")
    git(repo, "config", "user.email", "fixture@example.test")
    write_files(repo, {"README.md": "# demo-calc\n\nA tiny calculator library.\n", **files})
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "fixture")
    if previous:
        set_up_with(previous["ref"], repo, LEGACY_VARS, previous.get("hosts", "claude,codex,cursor"))
    return repo


def main() -> None:
    spec = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    build(Path(sys.argv[1]).resolve(), spec.get("files", {}), spec.get("previous"))


if __name__ == "__main__":
    main()
