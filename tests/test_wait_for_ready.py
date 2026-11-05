"""`--ready` waits for CI, then the review the repo runs. `--sha` and `--pr` name the commit."""

import json
import os
import stat
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from test_wait_for_checks import check

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/wait-for-action/scripts/wait-for-action.sh"
HEAD = "f00dfeed"
BOT_CHECK_URL = "https://example.test/check"

FAKE_GH = """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path

world = json.loads(Path(os.environ["WFA_WORLD"]).read_text())
args = sys.argv[1:]
line = " ".join(args)
with Path(os.environ["WFA_GH_LOG"]).open("a") as fh:
    fh.write(line + "\\n")

if args[:2] == ["pr", "view"]:
    if "headRefOid" in args:
        print(world["head"])
    else:
        print("https://example.test/pull/7" if "url" in args else "7")
elif args[:2] == ["pr", "checks"]:
    json.dump(world["checks"], sys.stdout)
elif args[:2] == ["run", "view"]:
    print("build\\tstep\\t2026-11-03T00:00:00.0000000Z ##[error] boom")
elif args[:2] == ["repo", "view"]:
    print(json.dumps({"owner": {"login": "o"}, "name": "r"}))
elif args[:1] == ["api"] and "graphql" in args:
    page = {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": world["threads"]}
    print(json.dumps({"data": {"repository": {"pullRequest": {"reviewThreads": page}}}}))
elif args[:1] == ["api"] and "/check-runs" in line:
    print(json.dumps({"check_runs": world["check_runs"]}))
elif args[:1] == ["api"] and line.endswith("/status"):
    print(json.dumps({"statuses": []}))
elif args[:1] == ["api"] and line.endswith("/pulls"):
    print(json.dumps([{"number": 7, "state": "open"}]))
elif args[:1] == ["api"] and "--jq" in args:
    print(world["head_time"])
elif args[:1] == ["api"] and "/comments" in line and "POST" not in args:
    print(json.dumps([world["comments"]]))
elif args[:1] == ["api"] and "POST" in args:
    pass
else:
    print("unexpected gh: " + line, file=sys.stderr)
    sys.exit(9)
"""


def now_stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def coderabbit_run(status="completed", conclusion="success", title="Review completed"):
    return {
        "id": 1,
        "name": "CodeRabbit",
        "status": status,
        "conclusion": conclusion,
        "html_url": BOT_CHECK_URL,
        "started_at": now_stamp(),
        "output": {"title": title},
    }


def thread(path="app.py"):
    return {
        "id": "T1",
        "isResolved": False,
        "isOutdated": False,
        "path": path,
        "line": 3,
        "originalLine": 3,
        "comments": {"nodes": [{"author": {"login": "coderabbitai"}, "body": "**Major**\n\n**Leaks a file**"}]},
    }


def rate_limit_notice():
    body = "<!-- rate limited by coderabbit.ai -->\n**Next included review available in 23 minutes.**"
    stamp = now_stamp()
    return {"user": {"login": "coderabbitai[bot]"}, "body": body, "updated_at": stamp, "created_at": stamp}


def world(checks, check_runs=(), threads=(), comments=(), head_time="2000-01-01T00:00:00Z"):
    return {
        "head": HEAD,
        "checks": checks,
        "check_runs": list(check_runs),
        "threads": list(threads),
        "comments": list(comments),
        "head_time": head_time,
    }


def passing_ci(*extra):
    return [check("build", "SUCCESS", workflow="ci"), *extra]


def run_script(tmp_path, scenario, args, cwd=None, settle="0"):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    world_file = tmp_path / "world.json"
    world_file.write_text(json.dumps(scenario))
    log = tmp_path / "gh.log"
    log.write_text("")
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["WFA_WORLD"] = str(world_file)
    env["WFA_GH_LOG"] = str(log)
    env["WFA_SETTLE_FOR"] = settle
    env["WFA_REGISTER_FOR"] = "0"
    env["WFA_INTERVAL"] = "1"
    started = time.monotonic()
    proc = subprocess.run(
        [str(SCRIPT), *args, "--log-dir", str(tmp_path / "logs")],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd or tmp_path,
        timeout=60,
    )
    proc.elapsed = time.monotonic() - started
    proc.gh_log = log.read_text()
    return proc


def test_ci_green_then_review_done_is_one_terminal_line_and_exit_0(tmp_path):
    scenario = world(passing_ci(check("CodeRabbit", "SUCCESS")), [coderabbit_run()], [thread()])

    proc = run_script(tmp_path, scenario, ["--ready", "--pr", "7", "--ttl", "30s"])

    terminal = [line for line in proc.stdout.splitlines() if " DONE " in line]
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert len(terminal) == 1
    assert "app.py:3" in proc.stdout


def test_ci_failure_returns_before_the_review_is_waited_on(tmp_path):
    scenario = world(passing_ci(check("lint", "FAILURE", workflow="ci"), check("CodeRabbit", "IN_PROGRESS")))

    proc = run_script(tmp_path, scenario, ["--ready", "--pr", "7", "--ttl", "30s"])

    assert proc.returncode == 1
    assert "check-runs" not in proc.gh_log


def test_a_failed_coderabbit_check_fails_the_wait(tmp_path):
    scenario = world(passing_ci(check("CodeRabbit", "FAILURE")))

    proc = run_script(tmp_path, scenario, ["--ready", "--pr", "7", "--ttl", "30s"])

    assert proc.returncode == 1
    assert "name='CodeRabbit'" in proc.stdout


def test_a_rate_limited_review_exits_4_not_reviewed(tmp_path):
    scenario = world(
        passing_ci(check("CodeRabbit", "SUCCESS")),
        [coderabbit_run(title="Rate limit exceeded")],
        comments=[rate_limit_notice()],
    )

    proc = run_script(tmp_path, scenario, ["--ready", "--pr", "7", "--ttl", "30s"])

    assert proc.returncode == 4, proc.stdout + proc.stderr
    assert "NOT_REVIEWED" in proc.stdout


def test_no_trigger_reaches_the_review_wait(tmp_path):
    scenario = world(
        passing_ci(check("CodeRabbit", "SUCCESS")),
        [coderabbit_run(conclusion="skipped", title="Review skipped")],
    )

    proc = run_script(tmp_path, scenario, ["--ready", "--pr", "7", "--ttl", "30s", "--no-trigger"])

    assert proc.returncode == 4
    assert "POST" not in proc.gh_log


def test_one_ttl_covers_both_phases(tmp_path):
    scenario = world(passing_ci(check("CodeRabbit", "SUCCESS")), [coderabbit_run(status="in_progress")])

    proc = run_script(tmp_path, scenario, ["--ready", "--pr", "7", "--ttl", "4s"], settle="3")

    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "TIMEOUT" in proc.stdout
    assert proc.elapsed < 6.5


def test_ci_that_uses_the_whole_ttl_leaves_no_review_wait(tmp_path):
    scenario = world(passing_ci(check("CodeRabbit", "SUCCESS")), [coderabbit_run()])

    proc = run_script(tmp_path, scenario, ["--ready", "--pr", "7", "--ttl", "2s"], settle="2")

    assert proc.returncode == 2
    assert "check-runs" not in proc.gh_log


def test_without_a_reviewer_it_is_the_checks_wait(tmp_path):
    proc = run_script(tmp_path, world(passing_ci()), ["--ready", "--pr", "7", "--ttl", "30s"])

    assert proc.returncode == 0
    assert "DONE pass" in proc.stdout
    assert "check-runs" not in proc.gh_log


def test_a_pr_agent_workflow_selects_the_pr_agent_review(tmp_path):
    review = {
        "user": {"login": "pr-agent[bot]", "type": "Bot"},
        "body": "<!-- pr-agent:review:full -->\nfindings",
        "updated_at": now_stamp(),
        "created_at": now_stamp(),
        "html_url": "https://example.test/comment",
    }
    scenario = world(passing_ci(check("review", "SUCCESS", workflow="PR Agent")), comments=[review])

    proc = run_script(tmp_path, scenario, ["--ready", "--pr", "7", "--ttl", "30s"])

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "DONE pr-agent" in proc.stdout
    assert "check-runs" not in proc.gh_log


def test_the_review_reads_the_head_of_the_pr_when_git_is_unusable(tmp_path):
    scenario = world(passing_ci(check("CodeRabbit", "SUCCESS")), [coderabbit_run()])

    proc = run_script(tmp_path, scenario, ["--ready", "--pr", "7", "--ttl", "30s"])

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"commits/{HEAD}/check-runs" in proc.gh_log


def test_coderabbit_with_pr_reads_the_pr_head(tmp_path):
    scenario = world([], [coderabbit_run()])

    proc = run_script(tmp_path, scenario, ["--coderabbit", "--pr", "7", "--ttl", "30s"])

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"commits/{HEAD}/check-runs" in proc.gh_log


def test_coderabbit_with_sha_needs_no_git_and_no_gh_lookup(tmp_path):
    scenario = world([], [coderabbit_run()])

    proc = run_script(tmp_path, scenario, ["--coderabbit", "--sha", "abc123", "--ttl", "30s"])

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "commits/abc123/check-runs" in proc.gh_log
    assert "headRefOid" not in proc.gh_log


def test_coderabbit_without_sha_or_pr_still_needs_git(tmp_path):
    proc = run_script(tmp_path, world([]), ["--coderabbit", "--ttl", "30s"])

    assert proc.returncode == 3


def test_sha_picks_the_run_to_watch_without_git(tmp_path):
    proc = run_script(tmp_path, world([]), ["--sha", "abc123", "--ttl", "5s"])

    assert "abc123" in proc.gh_log
    assert proc.returncode == 3


def test_usage_conflicts(tmp_path):
    cases = (
        ["--ready", "--checks"],
        ["--ready", "--coderabbit"],
        ["--ready", "--run-id", "1"],
        ["--checks", "--sha", "abc"],
        ["--pr", "5"],
        ["--no-trigger"],
        ["--coderabbit", "--pr", "abc"],
    )
    for args in cases:
        proc = run_script(tmp_path, world([]), args)
        assert proc.returncode == 3, args
