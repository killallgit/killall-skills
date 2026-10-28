import json
import subprocess
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parent.parent / "skills/ship/hooks/guard-merge.sh"
MERGE = "gh pr merge --squash --delete-branch"


def run_guard(tmp_path: Path, command: str, checks: list[dict]) -> int:
    gh = tmp_path / "gh"
    gh.write_text(f"#!/usr/bin/env bash\necho '{json.dumps(checks)}'\n")
    gh.chmod(0o755)
    payload = json.dumps({"tool_input": {"command": command}})
    env = {"PATH": f"{tmp_path}:/usr/bin:/bin:/opt/homebrew/bin"}
    return subprocess.run(
        [str(GUARD)], input=payload, text=True, env=env, capture_output=True
    ).returncode


def test_commands_other_than_a_merge_are_allowed(tmp_path):
    assert run_guard(tmp_path, "git status", []) == 0


def test_merge_is_allowed_when_the_coderabbit_check_succeeded(tmp_path):
    checks = [{"name": "CodeRabbit", "state": "SUCCESS"}]

    assert run_guard(tmp_path, MERGE, checks) == 0


@pytest.mark.parametrize("state", ["PENDING", "FAILURE"])
def test_merge_is_blocked_while_the_coderabbit_check_is_not_successful(tmp_path, state):
    checks = [{"name": "CodeRabbit", "state": state}]

    assert run_guard(tmp_path, MERGE, checks) == 2


def test_merge_is_blocked_when_there_is_no_coderabbit_check(tmp_path):
    checks = [{"name": "tests", "state": "SUCCESS"}]

    assert run_guard(tmp_path, MERGE, checks) == 2
