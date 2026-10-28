# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
import json
import re
import subprocess
import sys
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


def sync_steps() -> list[list[str]]:
    return [
        ["git", "fetch", "origin", "--tags"],
        ["git", "switch", "main"],
        ["git", "pull", "--rebase", "origin", "main"],
    ]


def publish_steps(version: str) -> list[list[str]]:
    tag = f"v{version}"
    return [
        ["git", "add", *RELEASE_FILES],
        ["git", "commit", "-m", f"chore: release {tag}"],
        ["git", "tag", "-a", tag, "-m", tag],
        ["git", "push", "--atomic", "origin", "main", tag],
    ]


def run(step: list[str]) -> None:
    subprocess.run(step, check=True)


def output(step: list[str]) -> str:
    return subprocess.run(step, check=True, capture_output=True, text=True).stdout


def release(root: Path, level: str) -> str:
    if output(["git", "status", "--porcelain"]).strip():
        raise SystemExit("working tree is not clean")
    for step in sync_steps():
        run(step)
    config_path = root / "marketplace.config.json"
    config = json.loads(config_path.read_text())
    config["version"] = bump_version(config["version"], level)
    tag = f"v{config['version']}"
    if output(["git", "tag", "--list", tag]).strip():
        raise SystemExit(f"{tag} already exists")
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    write_files(generated_files(root))
    for step in publish_steps(config["version"]):
        run(step)
    return tag


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
