from datetime import datetime, timezone

import pytest

import coderabbit
from coderabbit import (
    TRIGGER,
    GhError,
    already_triggered,
    ci_summary,
    classify,
    coderabbit_check,
    rate_limit_seconds,
    summarize_thread,
    watch,
)

SHA = "abc123"
T0 = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc).timestamp()


def stamp(offset: float) -> str:
    return datetime.fromtimestamp(T0 + offset, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check(id=1, status="completed", conclusion="success", title="Review completed", name="CodeRabbit", started=-5):
    return {
        "id": id,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "html_url": "https://example.test/check",
        "started_at": stamp(started),
        "output": {"title": title},
    }


def limit_notice(minutes=23, updated=0):
    body = f"<!-- rate limited by coderabbit.ai -->\n**Next included review available in {minutes} minutes.**"
    return {"user": {"login": coderabbit.BOT}, "body": body, "updated_at": stamp(updated), "created_at": stamp(updated)}


def human_trigger(at):
    return {"user": {"login": "me"}, "body": TRIGGER, "updated_at": stamp(at), "created_at": stamp(at)}


class FakeClock:
    def __init__(self):
        self.t = T0

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


class FakeClient:
    """`scripts` maps a call count of check_runs to the runs it returns; the last one repeats."""

    def __init__(self, clock, scripts, comments=None, pr=7, threads=None):
        self.clock, self.scripts, self.pr = clock, scripts, pr
        self.calls = 0
        self.posted = []
        self.posted_at = []
        self.existing = comments or []
        self.threads = threads or []
        self.legacy = None

    def check_runs(self, sha):
        runs = self.scripts[min(self.calls, len(self.scripts) - 1)]
        self.calls += 1
        if isinstance(runs, Exception):
            raise runs
        return runs(self.clock) if callable(runs) else runs

    def legacy_status(self, sha):
        return self.legacy

    def open_pr(self, sha):
        return self.pr

    def comments(self, pr):
        return self.existing + [human_trigger(at) for at in self.posted_at]

    def comment(self, pr, body):
        self.posted.append(body)
        self.posted_at.append(self.clock.now() - T0)

    def unresolved_threads(self, pr):
        return self.threads


def run_watch(client, clock, ttl=900, trigger=True):
    lines, saved = [], {}
    code = watch(
        client, SHA, ttl, clock,
        lambda always, line: lines.append(line),
        lambda name, data: saved.update({name: data}),
        trigger=trigger,
    )
    return code, lines, saved


def test_the_newest_check_after_the_floor_is_the_one_that_counts():
    runs = [check(id=1), check(id=3), check(id=2), check(id=9, name="manifests")]

    assert coderabbit_check(runs, 0)["id"] == 3
    assert coderabbit_check(runs, 3) is None


@pytest.mark.parametrize(
    ("run", "kind"),
    [
        (check(), "DONE"),
        (check(status="in_progress", conclusion=None), "PENDING"),
        (check(conclusion="failure", title="Review failed"), "FAILED"),
        (check(conclusion="neutral", title="Review rate limited"), "RATE_LIMITED"),
        (check(conclusion="neutral", title="Review skipped"), "SKIPPED"),
        (check(conclusion="skipped", title=""), "SKIPPED"),
        (check(conclusion="neutral", title="Review paused"), "SKIPPED"),
    ],
)
def test_check_runs_are_classified(run, kind):
    assert classify(run, None).kind == kind


def test_a_legacy_commit_status_is_read_when_there_is_no_check_run():
    assert classify(None, {"state": "success", "description": "Review completed"}).kind == "DONE"
    assert classify(None, {"state": "pending", "description": "Review in progress"}).kind == "PENDING"
    assert classify(None, {"state": "success", "description": "Review rate limited"}).kind == "RATE_LIMITED"
    assert classify(None, None).kind == "NONE"


def test_rate_limit_wait_counts_from_when_the_notice_was_written():
    comments = [limit_notice(minutes=23, updated=0)]

    assert rate_limit_seconds(comments, T0 + 300) == 23 * 60 - 300


def test_rate_limit_wait_is_none_without_a_notice_and_zero_once_passed():
    assert rate_limit_seconds([], T0) is None
    assert rate_limit_seconds([limit_notice(minutes=1)], T0 + 600) == 0


def test_rate_limit_wait_reads_the_wait_wording_too():
    body = "<!-- rate limited by coderabbit.ai -->\nPlease wait 4 minutes and 30 seconds before"
    notice = {"user": {"login": coderabbit.BOT}, "body": body, "updated_at": stamp(0)}

    assert rate_limit_seconds([notice], T0) == 270


def test_a_review_comment_made_after_the_check_counts_as_already_triggered():
    assert already_triggered([human_trigger(10)], T0)
    assert not already_triggered([human_trigger(-10)], T0)
    assert not already_triggered([{**human_trigger(10), "body": "looks good"}], T0)


def test_ci_summary_ignores_coderabbit():
    runs = [
        check(),
        check(id=2, name="tests"),
        check(id=3, name="lint", conclusion="failure"),
        check(id=4, name="build", status="in_progress", conclusion=None),
    ]

    assert ci_summary(runs) == "ci: 1 passed, 1 failed, 1 pending"


def test_thread_summary_strips_html_and_keeps_severity_and_title():
    thread = {
        "id": "T1",
        "path": "a.sh",
        "line": 3,
        "isOutdated": False,
        "comments": {"nodes": [{"body": "**<picture><img alt=\"\"></picture> Major** · **Correctness**\n\n**Block on failure.**\n\ndetail"}]},
    }

    assert summarize_thread(thread) == {
        "id": "T1", "path": "a.sh", "line": 3, "outdated": False, "severity": "Major", "title": "Block on failure.",
    }


def test_thread_summary_falls_back_to_the_original_line():
    thread = {
        "id": "T1", "path": "a.sh", "line": None, "originalLine": 9, "isOutdated": True,
        "comments": {"nodes": [{"body": "**Major** x"}]},
    }

    assert summarize_thread(thread)["line"] == 9


def test_a_pending_review_is_waited_out_until_done():
    clock = FakeClock()
    client = FakeClient(clock, [[check(status="in_progress", conclusion=None)], [check()]])

    code, lines, saved = run_watch(client, clock)

    assert code == 0
    assert any(line.startswith("DONE coderabbit Review completed") for line in lines)
    assert client.posted == []
    assert saved["findings.json"] == []


def test_done_lists_the_unresolved_findings():
    clock = FakeClock()
    thread = {"id": "T1", "path": "a.sh", "line": 3, "outdated": False, "severity": "Major", "title": "Fix it"}
    client = FakeClient(clock, [[check()]], threads=[thread])

    code, lines, saved = run_watch(client, clock)

    assert code == 0
    assert saved["findings.json"] == [thread]
    assert "  a.sh:3 Major Fix it" in lines


def test_a_failed_review_exits_1():
    clock = FakeClock()
    client = FakeClient(clock, [[check(conclusion="failure", title="Review failed")]])

    assert run_watch(client, clock)[0] == 1


def test_a_skipped_review_is_restarted_with_a_comment():
    clock = FakeClock()
    skipped = check(id=1, conclusion="neutral", title="Review skipped: label required")
    client = FakeClient(clock, [[skipped], [skipped], [skipped, check(id=2)]])

    code, lines, _ = run_watch(client, clock)

    assert code == 0
    assert client.posted == [TRIGGER]
    assert any(line.startswith("TRIGGERED coderabbit") for line in lines)


def test_a_review_that_is_skipped_again_after_the_comment_is_not_reviewed():
    clock = FakeClock()
    first = check(id=1, conclusion="neutral", title="Review skipped")
    second = check(id=2, conclusion="neutral", title="Review skipped")
    client = FakeClient(clock, [[first], [first, second]])

    code, lines, _ = run_watch(client, clock)

    assert code == 4
    assert client.posted == [TRIGGER]
    assert any(line.startswith("NOT_REVIEWED") for line in lines)


def test_skipped_is_reported_without_commenting_when_triggering_is_off():
    clock = FakeClock()
    client = FakeClient(clock, [[check(conclusion="neutral", title="Review skipped")]])

    code, _, _ = run_watch(client, clock, trigger=False)

    assert code == 4
    assert client.posted == []


def test_a_rate_limit_is_waited_out_then_restarted_with_a_comment():
    clock = FakeClock()
    limited = check(id=1, conclusion="neutral", title="Review rate limited")
    client = FakeClient(clock, [[limited], [limited], [limited, check(id=2)]], comments=[limit_notice(minutes=5)])

    code, lines, _ = run_watch(client, clock, ttl=1800)

    assert code == 0
    assert client.posted == [TRIGGER]
    assert clock.now() - T0 >= 5 * 60
    assert any(line.startswith("RATE_LIMITED coderabbit") for line in lines)


def test_a_rate_limit_that_is_still_on_after_the_comment_is_waited_out_again():
    clock = FakeClock()
    first = check(id=1, conclusion="neutral", title="Review rate limited")
    second = check(id=2, conclusion="neutral", title="Review rate limited", started=200)
    client = FakeClient(clock, [[first], [first], [first, second], [first, second], [first, second, check(id=3)]],
                        comments=[limit_notice(minutes=2)])

    code, _, _ = run_watch(client, clock, ttl=3600)

    assert code == 0
    assert client.posted == [TRIGGER, TRIGGER]


def test_a_rate_limit_longer_than_the_budget_is_not_reviewed_and_does_not_wait():
    clock = FakeClock()
    limited = check(conclusion="neutral", title="Review rate limited")
    client = FakeClient(clock, [[limited]], comments=[limit_notice(minutes=23)])

    code, lines, _ = run_watch(client, clock, ttl=900)

    assert code == 4
    assert clock.now() == T0
    assert "next review in 24m" in lines[-1]
    assert client.posted == []


def test_a_review_comment_already_on_the_pr_is_not_posted_twice():
    clock = FakeClock()
    skipped = check(id=1, conclusion="neutral", title="Review skipped")
    client = FakeClient(clock, [[skipped], [skipped, check(id=2)]], comments=[human_trigger(60)])

    code, _, _ = run_watch(client, clock)

    assert code == 0
    assert client.posted == []


def test_no_check_after_a_minute_on_an_open_pr_is_restarted_with_a_comment():
    clock = FakeClock()
    client = FakeClient(clock, [[]] * 14 + [[check(id=2)]])

    code, _, _ = run_watch(client, clock)

    assert code == 0
    assert client.posted == [TRIGGER]


def test_no_check_and_no_open_pr_is_an_error():
    clock = FakeClock()
    client = FakeClient(clock, [[]], pr=None)

    code, lines, _ = run_watch(client, clock)

    assert code == 3
    assert "no open PR" in lines[-1]


def test_a_review_that_never_starts_times_out():
    clock = FakeClock()
    client = FakeClient(clock, [[check(status="in_progress", conclusion=None)]])

    code, lines, _ = run_watch(client, clock, ttl=120)

    assert code == 2
    assert lines[-1].startswith("TIMEOUT")


def test_a_few_api_errors_are_retried_but_a_persistent_one_is_an_error():
    clock = FakeClock()
    flaky = FakeClient(clock, [GhError("boom"), GhError("boom"), [check()]])
    broken = FakeClient(clock, [GhError("boom")])

    assert run_watch(flaky, clock)[0] == 0
    assert run_watch(broken, clock)[0] == 3


def test_a_threadless_line_is_listed_by_path_only():
    clock = FakeClock()
    thread = {"id": "T1", "path": "a.sh", "line": None, "outdated": True, "severity": "Major", "title": "Fix it"}
    client = FakeClient(clock, [[check()]], threads=[thread])

    _, lines, _ = run_watch(client, clock)

    assert "  a.sh Major Fix it (outdated)" in lines


def test_an_unexpected_payload_shape_is_retried_then_an_error_not_a_failure():
    clock = FakeClock()
    client = FakeClient(clock, [KeyError("check_runs")])

    code, lines, _ = run_watch(client, clock)

    assert code == 3
    assert "KeyError" in lines[-1]


def test_the_legacy_status_is_only_read_when_there_is_no_check_run():
    clock = FakeClock()
    client = FakeClient(clock, [[check()]])
    client.legacy_status = lambda sha: pytest.fail("legacy status read")

    assert run_watch(client, clock)[0] == 0


def test_a_finished_review_whose_findings_cannot_be_read_is_an_error_not_a_clean_pass():
    clock = FakeClock()
    client = FakeClient(clock, [[check()]])

    def unreadable(pr):
        raise GhError("graphql down")

    client.unresolved_threads = unreadable

    code, lines, _ = run_watch(client, clock)

    assert code == 3
    assert "findings could not be read" in lines[-1]


def test_no_comment_is_posted_once_the_budget_ran_out_during_a_long_sleep():
    clock = FakeClock()
    limited = check(conclusion="neutral", title="Review rate limited")
    client = FakeClient(clock, [[limited]], comments=[limit_notice(minutes=2)])
    clock.sleep = lambda seconds: setattr(clock, "t", clock.t + 10_000)

    code, lines, _ = run_watch(client, clock, ttl=3600)

    assert code == 2
    assert lines[-1].startswith("TIMEOUT")
    assert client.posted == []
