#!/usr/bin/env python3
"""Wait for the PR-Agent review of HEAD, starting it with a `/review` comment.

Run through `wait-for-action.sh --pr-agent`. PR-Agent (qodo-ai/pr-agent) runs as
a GitHub Action or App and answers with one persistent comment carrying a
`<!-- pr-agent:review` marker, edited in place on each run. It posts no check
run, and its workflow runs on the default branch's commit, so HEAD cannot be
matched to a run. The review counts when that comment was last updated after
the HEAD commit was made.

Exit: 0 reviewed  2 ttl expired  3 error
"""
from __future__ import annotations

import sys

import coderabbit
from coderabbit import API_ERRORS, EXIT_DONE, EXIT_ERROR, EXIT_TIMEOUT, gh, parse_time

MARKER = "<!-- pr-agent:review"
TRIGGER = "/review"
PLACEHOLDER = "preparing review"


class GhClient(coderabbit.GhClient):
    def head_time(self, sha: str) -> str:
        return gh("api", f"repos/{{owner}}/{{repo}}/commits/{sha}", "--jq", ".commit.committer.date").strip()


def review_comment(comments: list[dict], since: float) -> dict | None:
    """Newest PR-Agent review comment updated after `since`."""
    found = [
        c for c in comments
        if c["user"]["type"] == "Bot" and MARKER in c["body"] and parse_time(c["updated_at"]) > since
    ]
    return max(found, key=lambda c: c["updated_at"], default=None)


def already_triggered(comments: list[dict], since: float) -> bool:
    return any(
        c["user"]["type"] != "Bot"
        and c["body"].strip().lower().startswith(TRIGGER)
        and parse_time(c["created_at"]) > since
        for c in comments
    )


def interval_for(elapsed: int) -> int:
    return 10 if elapsed < 120 else 30


def watch(client, sha: str, ttl: int, clock, say, save, trigger: bool = True) -> int:
    """`say(always, line)` prints a status line; `save(name, data)` keeps an artifact."""
    start = clock.now()
    pr = since = None
    errors = 0
    posted = False
    last = None

    def announce(kind: str, detail: str = "") -> None:
        nonlocal last
        if (kind, detail) != last:
            say(False, f"{kind} pr-agent {detail}".rstrip())
            last = (kind, detail)

    while True:
        try:
            pr = pr or client.open_pr(sha)
            if pr is None:
                say(True, f"ERROR no open PR for {sha}")
                return EXIT_ERROR
            since = since or parse_time(client.head_time(sha))
            comments = client.comments(pr)
            errors = 0
        except API_ERRORS as err:
            errors += 1
            if errors >= 3:
                say(True, f"ERROR {err!r}")
                return EXIT_ERROR
            announce("PENDING", f"api-error, retrying -- {err!r}")
            comments = None

        if comments is not None:
            review = review_comment(comments, since)
            if review and PLACEHOLDER not in review["body"].lower():
                save("review.md", review["body"])
                say(True, f"DONE pr-agent {review['html_url']}")
                say(False, "review: see review.md")
                return EXIT_DONE
            if trigger and not posted and not already_triggered(comments, since):
                try:
                    client.comment(pr, TRIGGER)
                except API_ERRORS as err:
                    say(True, f"ERROR {err!r}")
                    return EXIT_ERROR
                posted = True
                announce("TRIGGERED", f"commented '{TRIGGER}'")
            else:
                announce("PENDING", "waiting for the review")

        elapsed = int(clock.now() - start)
        if elapsed >= ttl:
            say(True, f"TIMEOUT pr-agent no review of HEAD after {ttl}s")
            return EXIT_TIMEOUT
        clock.sleep(min(interval_for(elapsed), ttl - elapsed))


if __name__ == "__main__":
    sys.exit(coderabbit.main(sys.argv[1:], watch, GhClient(), "pr-agent"))
