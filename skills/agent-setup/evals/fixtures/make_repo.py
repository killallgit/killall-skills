from __future__ import annotations

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
    top = git(Path(__file__).resolve().parent, "rev-parse", "--show-toplevel")
    dest.mkdir(parents=True, exist_ok=True)
    archive = dest / "skill.tar"
    with archive.open("wb") as handle:
        subprocess.run(["git", "-C", top, "archive", ref, SKILL_PATH], stdout=handle, check=True)
    with tarfile.open(archive) as tar:
        tar.extractall(dest)
    return dest / SKILL_PATH


def set_up_with(ref: str, repo: Path) -> None:
    """LEGACY_VARS holds every key any version reads; each version takes only the keys it knows."""
    with tempfile.TemporaryDirectory() as tmp:
        renderer = extract_skill(ref, Path(tmp)) / "scripts/render_agents.py"
        command = [sys.executable, str(renderer), "--dest", str(repo), "--vars", str(LEGACY_VARS)]
        subprocess.run(command, check=True, capture_output=True)


def build(repo: Path, files: dict[str, str], previous: dict[str, str] | None = None) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    git(repo, "config", "user.name", "Fixture")
    git(repo, "config", "user.email", "fixture@example.test")
    write_files(repo, {"README.md": "# demo-calc\n\nA tiny calculator library.\n", **files})
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "fixture")
    if previous:
        set_up_with(previous["ref"], repo)
    return repo
