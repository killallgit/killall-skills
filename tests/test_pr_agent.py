from datetime import datetime, timezone

import pytest

from coderabbit import GhError
from pr_agent import TRIGGER, already_triggered, review_comment, watch

SHA = "abc123"
T0 = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc).timestamp()


def stamp(offset: float) -> str:
    return datetime.fromtimestamp(T0 + offset, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def review(updated, body="## PR Reviewer Guide\n<!-- pr-agent:review:full -->\nfindings"):
    return {"user": {"type": "Bot", "login": "github-actions[bot]"}, "body": body,
            "created_at": stamp(updated - 60), "updated_at": stamp(updated), "html_url": "https://example.test/c"}


def human(at, body=TRIGGER):
    return {"user": {"type": "User", "login": "me"}, "body": body, "created_at": stamp(at), "updated_at": stamp(at)}


class FakeClock:
    def __init__(self):
        self.t = T0

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


class FakeClient:
    """`reviews_at` is the offset after which the bot's review comment exists; None means never."""

    def __init__(self, clock, reviews_at=None, existing=None, pr=7, head=-30, fail=None):
        self.clock, self.reviews_at, self.pr, self.head = clock, reviews_at, pr, head
        self.existing, self.posted, self.fail = existing or [], [], fail

    def open_pr(self, sha):
        return self.pr

    def head_time(self, sha):
        return stamp(self.head)

    def comments(self, pr):
        if self.fail:
            raise self.fail
        now = self.clock.now() - T0
        bot = [review(self.reviews_at)] if self.reviews_at is not None and now >= self.reviews_at else []
        return self.existing + [human(at) for at in self.posted_at()] + bot

    def posted_at(self):
        return [t for _, t in self.posted]

    def comment(self, pr, body):
        self.posted.append((body, self.clock.now() - T0))


def run(client, clock, ttl=300, trigger=True):
    lines, saved = [], {}
    code = watch(client, SHA, ttl, clock, lambda always, line: lines.append(line),
                 lambda name, data: saved.update({name: data}), trigger=trigger)
    return code, lines, saved


def test_a_review_updated_after_head_was_made_counts_and_an_older_one_does_not():
    assert review_comment([review(-60)], T0 - 30) is None
    assert review_comment([review(-10)], T0 - 30)["updated_at"] == stamp(-10)


def test_only_a_bot_comment_with_the_marker_is_a_review():
    other = review(0, body="coverage report")
    by_human = {**review(0), "user": {"type": "User", "login": "me"}}

    assert review_comment([other, by_human], T0 - 30) is None


def test_a_human_review_command_after_head_counts_as_triggered():
    assert already_triggered([human(-10)], T0 - 30)
    assert not already_triggered([human(-60)], T0 - 30)
    assert not already_triggered([human(-10, body="looks good")], T0 - 30)


def test_a_missing_review_is_started_once_then_waited_for():
    clock = FakeClock()
    client = FakeClient(clock, reviews_at=45)

    code, lines, saved = run(client, clock)

    assert code == 0
    assert [body for body, _ in client.posted] == [TRIGGER]
    assert "findings" in saved["review.md"]
    assert any(line.startswith("DONE pr-agent") for line in lines)


def test_a_review_already_on_head_needs_no_trigger():
    clock = FakeClock()
    client = FakeClient(clock, reviews_at=0)

    code, _, _ = run(client, clock)

    assert code == 0 and client.posted == []


def test_a_review_command_already_posted_since_head_is_not_repeated():
    clock = FakeClock()
    client = FakeClient(clock, reviews_at=60, existing=[human(-10)])

    code, _, _ = run(client, clock)

    assert code == 0 and client.posted == []


def test_a_placeholder_comment_is_not_a_finished_review():
    clock = FakeClock()
    client = FakeClient(clock, reviews_at=0, existing=[human(-10)])
    client.comments = lambda pr: [review(0, body="<!-- pr-agent:review:full -->\nPreparing review...")]

    code, lines, _ = run(client, clock, ttl=60)

    assert code == 2 and lines[-1].startswith("TIMEOUT pr-agent")


def test_no_trigger_reports_instead_of_commenting():
    clock = FakeClock()
    client = FakeClient(clock, reviews_at=None)

    code, _, _ = run(client, clock, ttl=60, trigger=False)

    assert code == 2 and client.posted == []


def test_no_open_pr_is_an_error():
    clock = FakeClock()

    code, lines, _ = run(FakeClient(clock, pr=None), clock)

    assert code == 3 and "no open PR" in lines[-1]


def test_an_api_that_keeps_failing_is_an_error():
    clock = FakeClock()

    code, lines, _ = run(FakeClient(clock, fail=GhError("boom")), clock)

    assert code == 3 and lines[-1].startswith("ERROR")
