import json
import subprocess
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parent.parent / "skills/ship/hooks/guard-merge.sh"
MERGE = "gh pr merge --squash --delete-branch"
PASSING = [{"name": "CodeRabbit", "state": "SUCCESS"}]


def run_guard(
    tmp_path: Path, command: str, checks: list[dict], payload: str | None = None, gh_body: str = "", timeout: str = "10"
) -> int:
    gh = tmp_path / "gh"
    gh.write_text(
        f"#!/usr/bin/env bash\necho \"$@\" > '{tmp_path}/gh-args'\n{gh_body}echo '{json.dumps(checks)}'\n"
    )
    gh.chmod(0o755)
    payload = payload or json.dumps({"tool_input": {"command": command}})
    env = {"PATH": f"{tmp_path}:/usr/bin:/bin:/opt/homebrew/bin", "GUARD_GH_TIMEOUT": timeout}
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
        ("gh pr merge --squash", "pr checks --json name,state,description"),
        ("gh pr merge 42 --squash", "pr checks 42 --json name,state,description"),
        ("gh pr merge --squash 42", "pr checks 42 --json name,state,description"),
        ("gh pr merge https://github.com/o/r/pull/42", "pr checks https://github.com/o/r/pull/42 --json name,state,description"),
        ("gh pr merge my-branch --delete-branch", "pr checks my-branch --json name,state,description"),
        ("gh -R o/r pr merge 42", "pr checks 42 -R o/r --json name,state,description"),
        ("gh pr merge 42 --repo o/r", "pr checks 42 -R o/r --json name,state,description"),
        ("gh pr merge 42 --subject fix && git pull", "pr checks 42 --json name,state,description"),
    ],
)
def test_the_checked_pr_is_the_one_being_merged(coderabbit_repo, command, expected):
    assert run_guard(coderabbit_repo, command, PASSING) == 0
    assert checks_args(coderabbit_repo) == expected


def test_merge_is_blocked_when_more_than_one_pr_is_named(coderabbit_repo):
    assert run_guard(coderabbit_repo, "gh pr merge 41 42", PASSING) == 2


def test_merge_is_blocked_when_the_hook_input_cannot_be_read(coderabbit_repo):
    assert run_guard(coderabbit_repo, "", PASSING, payload="not json") == 2


def test_merge_is_blocked_when_the_coderabbit_check_only_shares_a_prefix(coderabbit_repo):
    checks = [{"name": "CodeRabbit lint", "state": "SUCCESS"}]

    assert run_guard(coderabbit_repo, MERGE, checks) == 2


def test_merge_is_blocked_when_gh_stalls(coderabbit_repo):
    assert run_guard(coderabbit_repo, MERGE, PASSING, gh_body="exec sleep 30\n", timeout="1") == 2


def test_merge_is_blocked_when_gh_fails(coderabbit_repo):
    assert run_guard(coderabbit_repo, MERGE, PASSING, gh_body="exit 1\n") == 2


def test_merge_is_blocked_when_a_compound_command_merges_twice(coderabbit_repo):
    assert run_guard(coderabbit_repo, "gh pr merge 41 && gh pr merge 42", PASSING) == 2


@pytest.mark.parametrize("description", ["Review rate limited", "Review skipped", "Review paused"])
def test_merge_is_blocked_when_a_successful_status_reports_no_review(coderabbit_repo, description):
    checks = [{"name": "CodeRabbit", "state": "SUCCESS", "description": description}]

    assert run_guard(coderabbit_repo, MERGE, checks) == 2


def test_merge_is_allowed_when_the_status_describes_a_finished_review(coderabbit_repo):
    checks = [{"name": "CodeRabbit", "state": "SUCCESS", "description": "Review completed"}]

    assert run_guard(coderabbit_repo, MERGE, checks) == 0


def run_without_jq(tmp_path: Path, command: str) -> int:
    for tool in ("bash", "env", "cat", "git"):
        link = tmp_path / tool
        if not link.exists():
            link.symlink_to(subprocess.run(["which", tool], capture_output=True, text=True).stdout.strip())
    payload = json.dumps({"tool_input": {"command": command}})
    return subprocess.run(
        [str(GUARD)], input=payload, text=True, env={"PATH": str(tmp_path)}, capture_output=True, cwd=tmp_path
    ).returncode


def test_without_jq_unrelated_commands_pass_and_merges_are_blocked(tmp_path):
    assert run_without_jq(tmp_path, "git status") == 0
    assert run_without_jq(tmp_path, MERGE) == 2


def test_a_word_ending_in_gh_is_not_a_merge(coderabbit_repo):
    assert run_guard(coderabbit_repo, "echo high pr merge notes", []) == 0


@pytest.mark.parametrize("exit_code", [1, 8])
def test_failed_or_pending_ci_does_not_hide_a_finished_coderabbit_review(coderabbit_repo, exit_code):
    body = f"echo '{json.dumps(PASSING)}'; exit {exit_code}\n"

    assert run_guard(coderabbit_repo, MERGE, [], gh_body=body) == 0


def test_the_repo_a_merge_cds_into_decides_whether_it_is_guarded(tmp_path):
    guarded = tmp_path / "guarded"
    guarded.mkdir()
    (guarded / ".coderabbit.yaml").write_text("")

    assert run_guard(tmp_path, f"cd {guarded} && {MERGE}", []) == 2
    assert run_guard(tmp_path, f"cd {tmp_path} && {MERGE}", []) == 0


def test_a_merge_for_another_repo_is_guarded_only_when_that_repo_uses_coderabbit(tmp_path):
    guarded = "gh pr merge 42 -R o/guarded"
    unguarded = "gh pr merge 42 -R o/other"
    body = 'if [[ "$*" == *guarded/contents* ]]; then exit 0; fi\n[[ "$1" == api ]] && exit 1\n'

    assert run_guard(tmp_path, guarded, [], gh_body=body) == 2
    assert run_guard(tmp_path, unguarded, [], gh_body=body) == 0
