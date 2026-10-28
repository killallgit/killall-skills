# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from generate_manifests import generated_files, write_files

SEMVER = re.compile(r"\A(\d+)\.(\d+)\.(\d+)\Z")
LEVELS = ("patch", "minor", "major")
RELEASE_FILES = [".claude-plugin/marketplace.json", "marketplace.config.json"]


def bump_version(current: str, level: str) -> str:
    match = SEMVER.match(current)
    if match is None:
        raise ValueError(f"not a major.minor.patch version: {current}")
    if level not in LEVELS:
        raise ValueError(f"level must be one of {LEVELS}")
    major, minor, patch = map(int, match.groups())
    bumped = {
        "major": (major + 1, 0, 0),
        "minor": (major, minor + 1, 0),
        "patch": (major, minor, patch + 1),
    }[level]
    return ".".join(map(str, bumped))


def check_steps() -> list[list[str]]:
    return [
        ["uv", "run", "--python", "3.12", "--with", "pytest", "--with", "pyyaml", "pytest"],
        ["uv", "run", "--python", "3.12", "scripts/generate_manifests.py", "--check"],
    ]


def publish_steps(version: str) -> list[list[str]]:
    tag = f"v{version}"
    return [
        ["git", "add", *RELEASE_FILES],
        ["git", "commit", "-m", f"chore: release {tag}"],
        ["git", "tag", "-a", tag, "-m", tag],
        ["git", "push", "--atomic", "origin", "HEAD:main", tag],
    ]


GIT_LOCATION_VARS = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"}


def clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in GIT_LOCATION_VARS}


def run(step: list[str], cwd: Path) -> None:
    subprocess.run(step, check=True, cwd=cwd, env=clean_env())


def output(step: list[str], cwd: Path) -> str:
    return subprocess.run(
        step, check=True, capture_output=True, text=True, cwd=cwd, env=clean_env()
    ).stdout


def release_from(work: Path, level: str) -> str:
    for step in check_steps():
        run(step, work)
    config_path = work / "marketplace.config.json"
    config = json.loads(config_path.read_text())
    config["version"] = bump_version(config["version"], level)
    tag = f"v{config['version']}"
    if output(["git", "tag", "--list", tag], work).strip():
        raise SystemExit(f"{tag} already exists")
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    write_files(generated_files(work))
    try:
        for step in publish_steps(config["version"]):
            run(step, work)
    except subprocess.CalledProcessError:
        if output(["git", "tag", "--list", tag], work).strip():
            run(["git", "tag", "-d", tag], work)
        raise
    return tag


def release(root: Path, level: str) -> str:
    run(["git", "fetch", "origin", "--tags"], root)
    with tempfile.TemporaryDirectory() as parent:
        work = Path(parent) / "release"
        run(["git", "worktree", "add", "--detach", str(work), "origin/main"], root)
        try:
            return release_from(work, level)
        finally:
            run(["git", "worktree", "remove", "--force", str(work)], root)


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in LEVELS:
        print(f"usage: release.py {'|'.join(LEVELS)}", file=sys.stderr)
        return 2
    try:
        tag = release(Path(__file__).resolve().parent.parent, argv[0])
    except subprocess.CalledProcessError as error:
        print(f"failed: {' '.join(error.cmd)}", file=sys.stderr)
        return 1
    print(f"released {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
