"""Read-only PR discovery; no real GitHub calls or sleeping."""
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

import pr_activity as activity
from test_coderabbit import check


class Clock:
    def __init__(self):
        self.t = 0

    def monotonic(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


def snapshot(checks=(), statuses=(), workflows=(), reviews=(), comments=(), requests=(), head="abc"):
    return dict(head=dict(number=7, headRefOid=head, url="https://example.test/pull/7", reviewRequests=list(requests)),
                checks=list(checks), statuses=list(statuses), workflows=list(workflows),
                reviews=list(reviews), comments=list(comments))


class Client:
    def __init__(self, *snapshots):
        self.snapshots = snapshots
        self.calls = 0

    def snapshot(self, pr):
        value = self.snapshots[min(self.calls, len(self.snapshots) - 1)]
        self.calls += 1
        if isinstance(value, Exception):
            raise value
        return value


def run(tmp_path, *snapshots, ttl=40, **kwargs):
    clock = Clock()
    client = Client(*snapshots)
    code = activity.watch(client, 7, ttl, tmp_path, clock=clock, settle=10, interval=5, **kwargs)
    return code, clock, (tmp_path / "poll.log").read_text()


def test_no_activity_settles_without_inventing_a_requirement(tmp_path):
    code, clock, log = run(tmp_path, snapshot())
    assert code == 5
    assert clock.t == 10
    assert "work may not have registered yet" in log


def test_queued_workflow_without_checks_is_running(tmp_path):
    workflow = dict(id=1, workflow_id=2, name="CI", event="push", status="queued", conclusion=None)
    code, _, log = run(tmp_path, snapshot(workflows=[workflow]), ttl=20)
    assert code == 2
    assert "workflow CI: queued" in log


def test_waits_for_current_check_to_finish(tmp_path):
    pending = snapshot(checks=[check(status="in_progress", conclusion=None)])
    code, _, log = run(tmp_path, pending, snapshot(checks=[check()]))
    assert code == 0
    assert "CodeRabbit: success" in log


def test_updated_same_check_id_is_not_discarded(tmp_path):
    skipped = snapshot(checks=[check(conclusion="neutral", title="Review skipped")])
    code, _, log = run(tmp_path, skipped, snapshot(checks=[check()]))
    assert code == 0
    assert "CodeRabbit: success" in log
    assert "TRIGGERED" not in log


@pytest.mark.parametrize("title", ["Review skipped", "Review rate limited", "Review paused"])
def test_non_running_coderabbit_does_not_burn_ttl(tmp_path, title):
    code, clock, log = run(tmp_path, snapshot(checks=[check(conclusion="neutral", title=title)]))
    assert code == 0
    assert clock.t == 10
    assert title.lower().split()[-1] in log.lower()


def test_copilot_request_without_acknowledgement_is_unconfirmed(tmp_path):
    code, clock, log = run(tmp_path, snapshot(requests=[dict(login="copilot-pull-request-reviewer[bot]")]))
    assert code == 5
    assert clock.t == 10
    assert "requested, start unconfirmed" in log


def test_current_and_old_reviews_are_distinguished():
    reviews = [dict(user=dict(login="coderabbitai[bot]"), commit_id="old", submitted_at="yesterday"),
               dict(user=dict(login="copilot-pull-request-reviewer[bot]"), commit_id="abc", submitted_at="today")]
    observations = activity.summarize(snapshot(reviews=reviews))["observations"]
    assert any("older-head review only" in o for o in observations)
    assert any("review submitted for current head" in o for o in observations)


def test_review_request_and_submitted_review_normalize_bot_suffix():
    report = activity.summarize(snapshot(
        requests=[dict(login="coderabbitai")],
        reviews=[dict(user=dict(login="coderabbitai[bot]"), commit_id="abc", submitted_at="today")],
    ))
    assert not any("start unconfirmed" in o for o in report["observations"])
    assert report["observed"] is True


def test_comment_is_not_proof_of_current_head_or_running_activity(tmp_path):
    comment = dict(id=1, user=dict(login="coderabbitai[bot]"), body="Review in progress")
    code, clock, log = run(tmp_path, snapshot(comments=[comment]))
    assert code == 5
    assert clock.t == 10
    assert "current-head activity unconfirmed" in log


def test_failure_is_not_hidden_by_pending_work(tmp_path):
    code, clock, _ = run(tmp_path, snapshot(checks=[check(conclusion="failure"), check(id=2, name="CI", status="queued")]))
    assert code == 1
    assert clock.t == 0


def test_no_fail_fast_waits_for_pending_work(tmp_path):
    failed = check(conclusion="failure")
    code, clock, _ = run(tmp_path, snapshot(checks=[failed, check(id=2, name="CI", status="queued")]),
                         snapshot(checks=[failed]), fail_fast=False)
    assert code == 1
    assert clock.t == 5


def test_newest_workflow_and_status_supersede_old_failures():
    workflows = [dict(id=1, workflow_id=2, event="push", name="CI", status="completed", conclusion="failure"),
                 dict(id=2, workflow_id=2, event="push", name="CI", status="completed", conclusion="success")]
    statuses = [dict(id=1, context="legacy", state="failure"), dict(id=2, context="legacy", state="success")]
    assert activity.summarize(snapshot(workflows=workflows, statuses=statuses))["failed"] == []


def test_changed_head_restarts_settle(tmp_path):
    code, clock, log = run(tmp_path, snapshot(), None, snapshot(head="new"))
    assert code == 5
    assert clock.t == 20
    assert "PR head changed" in log
    assert json.loads((tmp_path / "summary.json").read_text())["head"] == "new"


def test_api_errors_are_bounded_and_never_a_pass(tmp_path):
    code, clock, log = run(tmp_path, activity.GhError("offline"))
    assert code == 3
    assert clock.t == 10
    assert "ERROR discovery failed" in log


def test_a_discovery_error_breaks_the_stability_window(tmp_path):
    code, clock, _ = run(tmp_path, snapshot(), activity.GhError("offline"), snapshot())
    assert code == 5
    assert clock.t == 20


def test_short_ttl_is_respected(tmp_path):
    code, clock, _ = run(tmp_path, snapshot(), ttl=3)
    assert code == 2
    assert clock.t == 3


def test_gh_is_read_only_noninteractive_and_deadline_bounded(monkeypatch):
    calls = []
    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout="[]")
    monkeypatch.setattr(subprocess, "run", fake_run)
    client = activity.Client("owner/repo")
    client.deadline = activity.time.monotonic() + 5
    assert client.gh("api", "repos/{owner}/{repo}/statuses") == []
    args, kwargs = calls[0]
    assert "POST" not in args
    assert kwargs["env"]["GH_REPO"] == "owner/repo"
    assert kwargs["env"]["GH_PROMPT_DISABLED"] == "1"
    assert 0 < kwargs["timeout"] <= 5


def test_snapshot_fetches_paginated_sources_and_rechecks_head():
    class Fake(activity.Client):
        def __init__(self):
            self.paths = []
            self.reads = 0
        def gh(self, *args):
            self.reads += 1
            return dict(number=7, headRefOid="abc", url="url", reviewRequests=[])
        def pages(self, path):
            self.paths.append(path)
            if "check-runs" in path:
                return [dict(check_runs=[check()]), dict(check_runs=[check(id=2, name="CI")])]
            if "actions/runs" in path:
                return [dict(workflow_runs=[])]
            return [[]]
    client = Fake()
    result = client.snapshot(7)
    assert len(result["checks"]) == 2
    assert client.reads == 2
    assert len(client.paths) == 5
    assert all("per_page=100" in p for p in client.paths)


@pytest.mark.parametrize("options", [[], ["--pr", "7", "--repo", "owner/repo"]])
def test_default_shell_routes_to_read_only_discovery(tmp_path, options):
    gh = tmp_path / "gh"
    gh.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ["CALLS"]).open("a") as f:
    f.write(json.dumps(args) + "\\n")
if args[:2] == ["pr", "view"]:
    print(json.dumps(dict(number=7, url="https://example.test/pull/7", headRefOid="abc", reviewRequests=[])))
elif "check-runs" in args[-1]:
    print(json.dumps([dict(check_runs=[dict(id=1, name="CI", status="completed", conclusion="failure")])] ))
elif "actions/runs" in args[-1]:
    print(json.dumps([dict(workflow_runs=[])]))
elif args[0] == "api":
    print("[[]]")
else:
    sys.exit(9)
''')
    gh.chmod(0o755)
    calls = tmp_path / "calls.jsonl"
    script = Path(__file__).resolve().parents[1] / "skills/wait-for-action/scripts/wait-for-action.sh"
    result = subprocess.run(["bash", str(script), *options, "--ttl", "10s", "--log-dir", str(tmp_path / "logs")],
                            env=dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", CALLS=str(calls)),
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAILED CI: failure" in result.stdout
    commands = [json.loads(line) for line in calls.read_text().splitlines()]
    assert len(commands) == 7
    assert all("POST" not in command and "-X" not in command for command in commands)
    assert (tmp_path / "logs/summary.json").exists()


@pytest.mark.parametrize("payload", [
    snapshot(checks=[dict(check(), app=None)]),
    snapshot(reviews=[dict(user=None, commit_id="abc", submitted_at="today")]),
    snapshot(comments=[dict(id=1, user=None, body="old comment")]),
])
def test_nullable_github_actors_and_apps_do_not_break_discovery(tmp_path, payload):
    code, _, log = run(tmp_path, payload)
    assert code == (0 if payload["checks"] else 5)
    assert "discovery error" not in log


def test_same_named_checks_from_different_suites_cannot_hide_failure():
    checks = [dict(check(id=1, name="lint", conclusion="failure"), app=dict(id=10), check_suite=dict(id=20)),
              dict(check(id=2, name="lint"), app=dict(id=10), check_suite=dict(id=30))]
    assert activity.summarize(snapshot(checks=checks))["failed"] == ["lint: failure"]


def test_check_rerun_in_same_suite_supersedes_prior_failure():
    checks = [dict(check(id=1, conclusion="failure"), app=dict(id=10), check_suite=dict(id=20)),
              dict(check(id=2), app=dict(id=10), check_suite=dict(id=20))]
    assert activity.summarize(snapshot(checks=checks))["failed"] == []


def test_missing_suite_metadata_does_not_hide_distinct_checks():
    checks = [check(id=1, name="lint", conclusion="failure"), check(id=2, name="lint")]
    assert activity.summarize(snapshot(checks=checks))["failed"] == ["lint: failure"]


def test_completion_warns_about_late_registration(tmp_path):
    code, _, log = run(tmp_path, snapshot(checks=[check()]))
    assert code == 0
    assert "Late-registering work may still appear" in log
    assert "not a merge/review approval" in log


def test_legacy_sha_lookup_cannot_silently_ignore_pr():
    script = Path(__file__).resolve().parents[1] / "skills/wait-for-action/scripts/wait-for-action.sh"
    result = subprocess.run(["bash", str(script), "--pr", "7", "--sha", "abc"],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 3
    assert "--pr does not combine" in result.stderr


def test_transport_timeout_at_deadline_is_ttl_not_success(monkeypatch):
    client = activity.Client()
    client.deadline = activity.time.monotonic() - 1
    with pytest.raises(TimeoutError):
        client.gh("api", "unused")
