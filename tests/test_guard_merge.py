import json
import subprocess
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parent.parent / "skills/ship/hooks/guard-merge.sh"
MERGE = "gh pr merge --squash --delete-branch"
PASSING = [{"name": "CodeRabbit", "state": "SUCCESS"}]


def run_guard(tmp_path: Path, command: str, checks: list[dict]) -> int:
    gh = tmp_path / "gh"
    gh.write_text(
        f"#!/usr/bin/env bash\necho \"$@\" > '{tmp_path}/gh-args'\necho '{json.dumps(checks)}'\n"
    )
    gh.chmod(0o755)
    payload = json.dumps({"tool_input": {"command": command}})
    env = {"PATH": f"{tmp_path}:/usr/bin:/bin:/opt/homebrew/bin"}
    return subprocess.run(
        [str(GUARD)], input=payload, text=True, env=env, capture_output=True, cwd=tmp_path
    ).returncode


def checks_args(tmp_path: Path) -> str:
    return (tmp_path / "gh-args").read_text().strip()


@pytest.fixture
def coderabbit_repo(tmp_path):
    (tmp_path / ".coderabbit.yaml").write_text("")
    return tmp_path


def test_commands_other_than_a_merge_are_allowed(coderabbit_repo):
    assert run_guard(coderabbit_repo, "git status", []) == 0


def test_merge_is_allowed_when_the_coderabbit_check_succeeded(coderabbit_repo):
    assert run_guard(coderabbit_repo, MERGE, PASSING) == 0


@pytest.mark.parametrize("state", ["PENDING", "FAILURE"])
def test_merge_is_blocked_while_the_coderabbit_check_is_not_successful(coderabbit_repo, state):
    checks = [{"name": "CodeRabbit", "state": state}]

    assert run_guard(coderabbit_repo, MERGE, checks) == 2


def test_merge_is_blocked_when_there_is_no_coderabbit_check(coderabbit_repo):
    checks = [{"name": "tests", "state": "SUCCESS"}]

    assert run_guard(coderabbit_repo, MERGE, checks) == 2


@pytest.mark.parametrize(
    "command",
    ["gh  pr  merge 42", "gh -R killallgit/killall-skills pr merge 42", "cd x && gh pr merge"],
)
def test_merge_variants_are_blocked_without_a_coderabbit_check(coderabbit_repo, command):
    assert run_guard(coderabbit_repo, command, []) == 2


def test_merge_is_allowed_in_a_repo_without_coderabbit_config(tmp_path):
    assert run_guard(tmp_path, MERGE, []) == 0


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("gh pr merge --squash", "pr checks --json name,state"),
        ("gh pr merge 42 --squash", "pr checks 42 --json name,state"),
        ("gh pr merge --squash 42", "pr checks 42 --json name,state"),
        ("gh pr merge https://github.com/o/r/pull/42", "pr checks https://github.com/o/r/pull/42 --json name,state"),
        ("gh pr merge my-branch --delete-branch", "pr checks my-branch --json name,state"),
        ("gh -R o/r pr merge 42", "pr checks 42 -R o/r --json name,state"),
        ("gh pr merge 42 --repo o/r", "pr checks 42 -R o/r --json name,state"),
        ("gh pr merge 42 --subject fix && git pull", "pr checks 42 --json name,state"),
    ],
)
def test_the_checked_pr_is_the_one_being_merged(coderabbit_repo, command, expected):
    assert run_guard(coderabbit_repo, command, PASSING) == 0
    assert checks_args(coderabbit_repo) == expected


def test_merge_is_blocked_when_more_than_one_pr_is_named(coderabbit_repo):
    assert run_guard(coderabbit_repo, "gh pr merge 41 42", PASSING) == 2
