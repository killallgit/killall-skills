"""`--checks` waits on the whole PR rollup: Actions, other check runs, and statuses."""

import json
import os
import stat
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/wait-for-action/scripts/wait-for-action.sh"
ZERO = "0001-01-01T00:00:00Z"
DONE = "2026-11-03T18:00:00Z"

FAKE_GH = """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path

log = Path(os.environ["WFA_GH_LOG"])
with log.open("a") as fh:
    fh.write(" ".join(sys.argv[1:]) + "\\n")

args = sys.argv[1:]
if "view" in args and "pr" in args:
    print("https://example.test/pull/7" if "url" in args else "7")
    sys.exit(0)
if "run" in args and "view" in args:
    sys.stdout.write("build\\tstep\\t2026-11-03T00:00:00.0000000Z ##[error] boom\\n")
    sys.exit(0)
if "checks" not in args:
    print("unexpected gh: " + " ".join(args), file=sys.stderr)
    sys.exit(9)

scenario = json.loads(Path(os.environ["WFA_SCENARIO"]).read_text())
state = Path(os.environ["WFA_STATE"])
idx = int(state.read_text() or "0")
steps = scenario["steps"]
step = steps[min(idx, len(steps) - 1)]
state.write_text(str(idx + 1))
if step.get("stderr"):
    print(step["stderr"], file=sys.stderr)
if "stdout" in step:
    sys.stdout.write(step["stdout"])
elif "json" in step:
    json.dump(step["json"], sys.stdout)
    sys.stdout.write("\\n")
sys.exit(step.get("exit", 0))
"""


def check(name, state, bucket=None, link="", workflow="", completed=DONE):
    if bucket is None:
        bucket = {
            "SUCCESS": "pass",
            "SKIPPED": "skipping",
            "NEUTRAL": "skipping",
            "CANCELLED": "cancel",
            "IN_PROGRESS": "pending",
            "QUEUED": "pending",
            "PENDING": "pending",
            "EXPECTED": "pending",
        }.get(state, "fail")
    return {
        "name": name,
        "state": state,
        "bucket": bucket,
        "link": link,
        "workflow": workflow,
        "completedAt": completed,
    }


def run(tmp_path, steps, extra_args=(), env_extra=None, timeout=20):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    scenario = tmp_path / "scenario.json"
    scenario.write_text(json.dumps({"steps": steps}))
    state = tmp_path / "state"
    state.write_text("0")
    log = tmp_path / "gh.log"
    log.write_text("")
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["WFA_SCENARIO"] = str(scenario)
    env["WFA_STATE"] = str(state)
    env["WFA_GH_LOG"] = str(log)
    env.setdefault("WFA_SETTLE_FOR", "0")
    env.setdefault("WFA_REGISTER_FOR", "0")
    env.setdefault("WFA_INTERVAL", "0")
    if env_extra:
        env.update(env_extra)
    started = time.monotonic()
    proc = subprocess.run(
        [str(SCRIPT), "--checks", "--pr", "7", "--ttl", "8s", "--log-dir", str(tmp_path / "logs"), *extra_args],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    proc.elapsed = time.monotonic() - started
    proc.calls = int(state.read_text() or "0")
    proc.gh_log = log.read_text()
    return proc


def empty_step():
    return {"exit": 1, "stderr": "no checks reported on the 'feat' branch"}


def test_pass_includes_an_actions_job_and_a_commit_status(tmp_path):
    proc = run(tmp_path, [{
        "json": [
            check("manifests", "SUCCESS", workflow="manifests",
                  link="https://github.com/o/r/actions/runs/1/job/2"),
            check("ci/circleci", "SUCCESS", link="https://circleci.example/1"),
        ],
    }])
    assert proc.returncode == 0, proc.stderr
    assert "DONE pass https://example.test/pull/7" in proc.stdout


def test_skipped_and_neutral_count_as_passed(tmp_path):
    proc = run(tmp_path, [{"json": [check("lint", "SKIPPED"), check("docs", "NEUTRAL")]}])
    assert proc.returncode == 0, proc.stdout
    assert "DONE skipped" in proc.stdout


def test_failure_names_the_check_and_pulls_an_actions_job_log(tmp_path):
    proc = run(tmp_path, [{
        "json": [
            check("manifests", "SUCCESS", workflow="manifests"),
            check("lint", "FAILURE", workflow="ci",
                  link="https://github.com/o/r/actions/runs/99/job/100"),
        ],
    }])
    assert proc.returncode == 1
    assert "name='lint'" in proc.stdout
    assert "name='manifests'" not in proc.stdout
    assert "##[error] boom" in proc.stdout
    assert "--job 100" in proc.gh_log


def test_states_gh_misbuckets_still_fail(tmp_path):
    for state, bucket in (
        ("CANCELLED", "cancel"),
        ("STARTUP_FAILURE", "pending"),
        ("STALE", "pending"),
        ("ACTION_REQUIRED", "fail"),
        ("TIMED_OUT", "fail"),
        ("ERROR", "fail"),
    ):
        proc = run(tmp_path, [{"json": [check("boot", state, bucket=bucket, workflow="ci")]}])
        assert proc.returncode == 1, state
        assert f"state='{state}'" in proc.stdout


def test_unknown_completed_state_fails(tmp_path):
    proc = run(tmp_path, [{"json": [check("odd", "MYSTERY", bucket="pending")]}])
    assert proc.returncode == 1
    assert "name='odd'" in proc.stdout


def test_json_is_read_when_gh_exits_1(tmp_path):
    """gh exits 1 for a failed check and for an empty rollup. The JSON decides."""
    proc = run(tmp_path, [{"exit": 1, "json": [check("manifests", "SUCCESS", workflow="ci")]}])
    assert proc.returncode == 0, proc.stderr
    assert "DONE pass" in proc.stdout


def test_no_checks_message_on_stdout_is_an_empty_rollup(tmp_path):
    proc = run(tmp_path, [{"exit": 1, "stdout": "no checks reported on the 'feat' branch\n"}])
    assert proc.returncode == 5
    assert "NONE no checks reported" in proc.stdout


def test_empty_rollup_waits_out_the_registration_window(tmp_path):
    proc = run(
        tmp_path,
        [empty_step(), {"json": [check("manifests", "SUCCESS", workflow="ci")]}],
        env_extra={"WFA_REGISTER_FOR": "5", "WFA_INTERVAL": "1"},
    )
    assert proc.returncode == 0, proc.stdout
    assert proc.calls >= 2


def test_empty_rollup_past_the_window_exits_none_before_ttl(tmp_path):
    proc = run(
        tmp_path,
        [empty_step()],
        extra_args=("--ttl", "30s"),
        env_extra={"WFA_REGISTER_FOR": "1", "WFA_INTERVAL": "1"},
    )
    assert proc.returncode == 5
    assert proc.elapsed < 8


def test_green_result_waits_for_a_check_that_registers_late(tmp_path):
    first = [check("manifests", "SUCCESS", workflow="manifests")]
    second = first + [check("lint", "SUCCESS", workflow="ci")]
    proc = run(
        tmp_path,
        [{"json": first}, {"json": second}],
        env_extra={"WFA_SETTLE_FOR": "2", "WFA_INTERVAL": "1"},
    )
    assert proc.returncode == 0, proc.stdout
    assert proc.calls >= 3


def test_failure_during_settle_stops_the_wait(tmp_path):
    proc = run(
        tmp_path,
        [
            {"json": [check("manifests", "SUCCESS", workflow="manifests")]},
            {"json": [
                check("manifests", "SUCCESS", workflow="manifests"),
                check("lint", "FAILURE", workflow="ci"),
            ]},
        ],
        env_extra={"WFA_SETTLE_FOR": "2", "WFA_INTERVAL": "1"},
    )
    assert proc.returncode == 1
    assert "name='lint'" in proc.stdout


def test_pending_then_pass(tmp_path):
    proc = run(tmp_path, [
        {"json": [check("manifests", "IN_PROGRESS", workflow="ci", completed=ZERO)]},
        {"json": [check("manifests", "SUCCESS", workflow="ci")]},
    ])
    assert proc.returncode == 0
    assert "DONE pass" in proc.stdout
    assert proc.calls >= 2


def test_no_fail_fast_waits_for_the_pending_check(tmp_path):
    proc = run(
        tmp_path,
        [
            {"json": [
                check("lint", "FAILURE", workflow="ci"),
                check("manifests", "IN_PROGRESS", workflow="manifests", completed=ZERO),
            ]},
            {"json": [
                check("lint", "FAILURE", workflow="ci"),
                check("manifests", "SUCCESS", workflow="manifests"),
            ]},
        ],
        extra_args=("--no-fail-fast",),
    )
    assert proc.returncode == 1
    assert proc.calls >= 2


def test_pending_until_ttl_exits_2(tmp_path):
    proc = run(
        tmp_path,
        [{"json": [check("manifests", "QUEUED", workflow="ci", completed=ZERO)]}],
        extra_args=("--ttl", "1s"),
    )
    assert proc.returncode == 2
    assert "TIMEOUT" in proc.stdout


def test_api_errors_exit_3(tmp_path):
    proc = run(tmp_path, [{"exit": 1, "stderr": "HTTP 502"}])
    assert proc.returncode == 3
    assert "ERROR" in proc.stdout
    assert proc.calls == 3


def test_usage_conflicts(tmp_path):
    env = os.environ.copy()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text("#!/bin/sh\nexit 0\n")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    cases = (
        ["--checks", "--run-id", "1"],
        ["--checks", "--coderabbit"],
        ["--pr", "5"],
        ["--checks", "--pr", "abc"],
    )
    for args in cases:
        proc = subprocess.run([str(SCRIPT), *args], capture_output=True, text=True, env=env)
        assert proc.returncode == 3, args
