import json
import subprocess
import sys
from pathlib import Path

import pytest

import release
from release import bump_version, check_steps, generate_step, publish_steps


@pytest.mark.parametrize(
    ("current", "level", "expected"),
    [
        ("1.2.3", "patch", "1.2.4"),
        ("1.2.3", "minor", "1.3.0"),
        ("1.2.3", "major", "2.0.0"),
        ("1.9.9", "minor", "1.10.0"),
    ],
)
def test_bump_version_increments_the_requested_part(current, level, expected):
    assert bump_version(current, level) == expected


def test_bump_version_rejects_unknown_level():
    with pytest.raises(ValueError):
        bump_version("1.2.3", "huge")


def test_bump_version_rejects_malformed_version():
    with pytest.raises(ValueError):
        bump_version("1.2", "patch")


def test_check_steps_run_the_tests_and_the_manifest_check():
    steps = check_steps()

    assert any("pytest" in step for step in steps)
    assert any(step[-2:] == ["scripts/generate_manifests.py", "--check"] for step in steps)


def test_publish_steps_tag_after_the_release_commit():
    verbs = [step[1] for step in publish_steps("1.3.0")]

    assert verbs.index("commit") < verbs.index("tag")


def test_publish_steps_push_branch_and_tag_atomically_last():
    last = publish_steps("1.3.0")[-1]

    assert last == ["git", "push", "--atomic", "origin", "HEAD:main", "v1.3.0"]


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=release.clean_env()
    ).stdout


@pytest.fixture
def checkout(tmp_path, monkeypatch):
    for key in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{key}_NAME", "tester")
        monkeypatch.setenv(f"GIT_{key}_EMAIL", "tester@example.com")
    monkeypatch.setattr(release, "check_steps", lambda: [])
    generator = Path(release.__file__).parent / "generate_manifests.py"
    monkeypatch.setattr(release, "generate_step", lambda: [sys.executable, "scripts/generate_manifests.py"])
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    clone = tmp_path / "clone"
    git(tmp_path, "clone", str(origin), str(clone))
    config = {
        "name": "m",
        "description": "d",
        "version": "1.0.0",
        "owner": {"name": "o"},
        "homepage": "h",
        "category": "c",
        "bundle": {"name": "b", "description": "d"},
    }
    (clone / "marketplace.config.json").write_text(json.dumps(config))
    (clone / "scripts").mkdir()
    (clone / "scripts" / "generate_manifests.py").write_text(generator.read_text())
    skill = clone / "skills" / "one"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: one\ndescription: first\n---\n")
    git(clone, "checkout", "-b", "main")
    git(clone, "add", ".")
    git(clone, "commit", "-m", "init")
    git(clone, "push", "-u", "origin", "main")
    return clone, origin


def test_release_pushes_the_bump_and_tag_without_touching_the_checkout(checkout):
    clone, origin = checkout
    git(clone, "switch", "-c", "feature")

    assert release.release(clone, "minor") == "v1.1.0"

    assert "v1.1.0" in git(origin, "tag", "--list")
    assert "chore: release v1.1.0" in git(origin, "log", "main", "--format=%s")
    assert git(clone, "branch", "--show-current").strip() == "feature"
    assert git(clone, "worktree", "list").count("\n") == 1


def test_release_leaves_no_tag_or_worktree_when_the_push_is_rejected(checkout):
    clone, origin = checkout
    hook = origin / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)

    with pytest.raises(subprocess.CalledProcessError):
        release.release(clone, "patch")

    assert git(clone, "tag", "--list").strip() == ""
    assert git(clone, "worktree", "list").count("\n") == 1
    assert git(origin, "tag", "--list").strip() == ""


def test_the_manifest_is_generated_by_the_script_in_the_release_checkout():
    assert generate_step()[-1] == "scripts/generate_manifests.py"


def test_release_regenerates_the_manifest_with_the_checkout_generator(checkout):
    clone, origin = checkout

    release.release(clone, "patch")

    manifest = json.loads(git(origin, "show", "main:.claude-plugin/marketplace.json"))
    assert {plugin["name"] for plugin in manifest["plugins"]} == {"b", "one"}
