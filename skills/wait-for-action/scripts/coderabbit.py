#!/usr/bin/env python3
"""Wait for the CodeRabbit review of HEAD, nudging it when it needs a push.

Run through `wait-for-action.sh --coderabbit`. CodeRabbit is a GitHub App that
reports a `CodeRabbit` check run (older installs: a commit status). Besides
pending and done it can be rate limited or skip the review (draft, missing
label, paused). Neither is final: `@coderabbitai review` on the PR starts it,
so this script posts that comment and keeps waiting.

Exit: 0 reviewed  1 failed  2 ttl expired  3 error  4 not reviewed
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BOT = "coderabbitai[bot]"
TRIGGER = "@coderabbitai review"
NO_CHECK_GRACE = 180
RETRY_PAD = 30
MAX_LIMIT_RETRIES = 4
EXIT_DONE, EXIT_FAILED, EXIT_TIMEOUT, EXIT_ERROR, EXIT_NOT_REVIEWED = 0, 1, 2, 3, 4

BAD_CONCLUSIONS = {"failure", "timed_out", "cancelled", "startup_failure", "action_required"}
UNITS = {"second": 1, "minute": 60, "hour": 3600}
RESET = re.compile(r"available in (\d+)\s*(second|minute|hour)", re.I)
WAIT = re.compile(r"wait (?:for )?(\d+) (minute|second|hour)s?(?: and (\d+) seconds?)?", re.I)
THREADS_QUERY = """query($owner:String!,$repo:String!,$n:Int!,$after:String){repository(owner:$owner,name:$repo){
pullRequest(number:$n){reviewThreads(first:100,after:$after){pageInfo{hasNextPage endCursor}
nodes{id isResolved isOutdated path line originalLine
comments(first:1){nodes{author{login} body}}}}}}}"""


class GhError(Exception):
    pass


# A payload that is not the shape we expect is as transient as a failed call.
API_ERRORS = (GhError, ValueError, KeyError, TypeError)


class Verdict:
    def __init__(self, kind: str, detail: str = "", url: str = "", check_id: int = 0):
        self.kind, self.detail, self.url, self.check_id = kind, detail, url, check_id


def parse_time(stamp: str) -> float:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()


def coderabbit_check(check_runs: list[dict], floor: int) -> dict | None:
    """Newest CodeRabbit check run newer than `floor`, a run id we already acted on."""
    runs = [run for run in check_runs if run["name"] == "CodeRabbit" and run["id"] > floor]
    return max(runs, key=lambda run: run["id"], default=None)


def classify_text(title: str, ok: bool) -> str:
    low = title.lower()
    if "rate limit" in low:
        return "RATE_LIMITED"
    if "skip" in low or "paus" in low:
        return "SKIPPED"
    return "DONE" if ok else "FAILED"


def classify(check: dict | None, legacy: dict | None) -> Verdict:
    if check is not None:
        title = (check.get("output") or {}).get("title") or ""
        url = check.get("html_url") or ""
        conclusion = check.get("conclusion")
        if check["status"] != "completed":
            return Verdict("PENDING", title or check["status"], url, check["id"])
        if conclusion in BAD_CONCLUSIONS:
            return Verdict("FAILED", title or conclusion, url, check["id"])
        kind = "SKIPPED" if conclusion == "skipped" else classify_text(title, True)
        return Verdict(kind, title or conclusion or "", url, check["id"])
    if legacy is not None:
        state, desc = legacy["state"], legacy.get("description") or ""
        url = legacy.get("target_url") or ""
        if state == "pending":
            return Verdict("PENDING", desc, url)
        if state in ("failure", "error"):
            return Verdict("FAILED", desc, url)
        return Verdict(classify_text(desc, True), desc, url)
    return Verdict("NONE")


def rate_limit_seconds(comments: list[dict], now: float) -> int | None:
    """Seconds until CodeRabbit's stated reset, read from its rate-limit notice."""
    notices = [
        c for c in comments
        if c["user"]["login"] == BOT and "rate limited by coderabbit.ai" in c["body"]
    ]
    if not notices:
        return None
    notice = max(notices, key=lambda c: c["updated_at"])
    match = RESET.search(notice["body"]) or WAIT.search(notice["body"])
    if match is None:
        return None
    seconds = int(match.group(1)) * UNITS[match.group(2).lower()]
    if match.re is WAIT and match.group(3):
        seconds += int(match.group(3))
    return max(0, int(parse_time(notice["updated_at"]) + seconds - now))


def already_triggered(comments: list[dict], since: float) -> bool:
    return any(
        c["user"]["login"] != BOT
        and c["body"].strip().lower().startswith(TRIGGER)
        and parse_time(c["created_at"]) > since
        for c in comments
    )


def ci_summary(check_runs: list[dict]) -> str:
    others = [run for run in check_runs if run["name"] != "CodeRabbit"]
    pending = sum(run["status"] != "completed" for run in others)
    failed = sum(run.get("conclusion") in BAD_CONCLUSIONS for run in others)
    return f"ci: {len(others) - pending - failed} passed, {failed} failed, {pending} pending"


def summarize_thread(thread: dict) -> dict:
    body = re.sub(r"<[^>]*>", "", thread["comments"]["nodes"][0]["body"])
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    severity = re.match(r"\*\*\s*(\w+)", lines[0]) if lines else None
    title = next((m.group(1) for m in (re.fullmatch(r"\*\*(.+)\*\*", l) for l in lines[1:]) if m), "")
    return {
        "id": thread["id"],
        "path": thread["path"],
        "line": thread["line"] or thread.get("originalLine"),
        "outdated": thread["isOutdated"],
        "severity": severity.group(1) if severity else "",
        "title": title or (lines[0][:80] if lines else ""),
    }


def interval_for(elapsed: int) -> int:
    if elapsed < 90:
        return 15
    if elapsed < 210:
        return 30
    if elapsed < 330:
        return 60
    return 180


GH_TIMEOUT = 60


def gh(*args: str) -> str:
    try:
        result = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=GH_TIMEOUT)
    except (subprocess.TimeoutExpired, OSError) as err:
        raise GhError(f"gh {' '.join(args[:2])}: {err}") from err
    if result.returncode:
        raise GhError(result.stderr.strip() or f"gh {' '.join(args)} failed")
    return result.stdout


class GhClient:
    def check_runs(self, sha: str) -> list[dict]:
        return json.loads(gh("api", f"repos/{{owner}}/{{repo}}/commits/{sha}/check-runs?per_page=100"))["check_runs"]

    def legacy_status(self, sha: str) -> dict | None:
        statuses = json.loads(gh("api", f"repos/{{owner}}/{{repo}}/commits/{sha}/status"))["statuses"]
        return next((s for s in statuses if s["context"] == "CodeRabbit"), None)

    def open_pr(self, sha: str) -> int | None:
        pulls = json.loads(gh("api", f"repos/{{owner}}/{{repo}}/commits/{sha}/pulls"))
        return next((p["number"] for p in pulls if p["state"] == "open"), None)

    def comments(self, pr: int) -> list[dict]:
        pages = json.loads(gh("api", "--paginate", "--slurp", f"repos/{{owner}}/{{repo}}/issues/{pr}/comments"))
        return [comment for page in pages for comment in page]

    def comment(self, pr: int, body: str) -> None:
        gh("api", "-X", "POST", f"repos/{{owner}}/{{repo}}/issues/{pr}/comments", "-f", f"body={body}")

    def unresolved_threads(self, pr: int) -> list[dict]:
        repo = json.loads(gh("repo", "view", "--json", "owner,name"))
        nodes, after = [], None
        while True:
            args = [
                "api", "graphql", "-f", f"query={THREADS_QUERY}",
                "-F", f"owner={repo['owner']['login']}", "-F", f"repo={repo['name']}", "-F", f"n={pr}",
            ]
            if after:
                args += ["-F", f"after={after}"]
            page = json.loads(gh(*args))["data"]["repository"]["pullRequest"]["reviewThreads"]
            nodes += page["nodes"]
            if not page["pageInfo"]["hasNextPage"]:
                break
            cursor = page["pageInfo"]["endCursor"]
            if not cursor or cursor == after:
                raise GhError("reviewThreads pagination did not advance")
            after = cursor
        return [
            summarize_thread(n) for n in nodes
            if not n["isResolved"] and n["comments"]["nodes"]
            and (n["comments"]["nodes"][0]["author"] or {}).get("login") == "coderabbitai"
        ]


class Clock:
    def now(self) -> float:
        return time.time()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


def watch(client, sha: str, ttl: int, clock, say, save, trigger: bool = True) -> int:
    """`say(always, line)` prints a status line; `save(name, data)` keeps an artifact."""
    start = clock.now()
    floor = triggers = errors = limit_retries = 0
    skip_nudged = False
    last = retry_at = pr = None

    def elapsed() -> int:
        return int(clock.now() - start)

    def announce(kind: str, detail: str = "") -> None:
        nonlocal last
        if (kind, detail) != last:
            say(False, f"{kind} coderabbit {detail}".rstrip())
            last = (kind, detail)

    def nudge(reason: str, check: dict | None) -> None:
        nonlocal floor, triggers
        since = parse_time(check["started_at"]) if check else start
        if not already_triggered(client.comments(pr), since):
            client.comment(pr, TRIGGER)
        triggers += 1
        floor = check["id"] if check else floor
        announce("TRIGGERED", f"{reason}; commented '{TRIGGER}'")

    def find_pr() -> int | None:
        nonlocal pr
        pr = pr or client.open_pr(sha)
        return pr

    def not_reviewed(detail: str) -> int:
        say(True, f"NOT_REVIEWED coderabbit {detail}")
        return EXIT_NOT_REVIEWED

    while True:
        verdict = None
        check = None
        try:
            runs = client.check_runs(sha)
            check = coderabbit_check(runs, floor)
            legacy = None if check or floor else client.legacy_status(sha)
            verdict = classify(check, legacy)
            errors = 0
        except API_ERRORS as err:
            errors += 1
            if errors >= 3:
                say(True, f"ERROR {err!r}")
                return EXIT_ERROR
            announce("PENDING", f"api-error, retrying -- {err!r}")

        nap = None
        if verdict is not None:
            kind = verdict.kind
            try:
                if kind == "DONE":
                    say(True, f"DONE coderabbit {verdict.detail} {verdict.url}".rstrip())
                    say(False, ci_summary(runs))
                    if not report_findings(client, sha, pr, say, save):
                        say(True, "ERROR review finished but its inline findings could not be read")
                        return EXIT_ERROR
                    return EXIT_DONE
                if kind == "FAILED":
                    say(True, f"FAILED coderabbit {verdict.detail} {verdict.url}".rstrip())
                    return EXIT_FAILED
                if kind == "PENDING":
                    announce("PENDING", verdict.detail)
                elif kind == "NONE" and elapsed() <= NO_CHECK_GRACE:
                    announce("PENDING", "no check yet")
                elif find_pr() is None:
                    say(True, f"ERROR no open PR for {sha}")
                    return EXIT_ERROR
                elif kind == "NONE":
                    if trigger and triggers == 0:
                        nudge("no review started", None)
                    else:
                        announce("PENDING", "waiting for CodeRabbit to start")
                elif kind == "SKIPPED":
                    if not trigger or skip_nudged:
                        return not_reviewed(f"{verdict.detail} {verdict.url}".strip())
                    skip_nudged = True
                    nudge(verdict.detail.lower(), check)
                else:
                    if not trigger or limit_retries >= MAX_LIMIT_RETRIES:
                        return not_reviewed(f"{verdict.detail} {verdict.url}".strip())
                    if retry_at is None:
                        wait = rate_limit_seconds(client.comments(pr), clock.now())
                        if wait is None:
                            return not_reviewed(f"{verdict.detail}, no reset time given")
                        if wait + RETRY_PAD > ttl - elapsed():
                            return not_reviewed(f"{verdict.detail}, next review in {wait // 60 + 1}m")
                        retry_at = clock.now() + wait + RETRY_PAD
                        announce("RATE_LIMITED", f"retrying in {wait // 60 + 1}m")
                    if clock.now() >= retry_at:
                        retry_at = None
                        limit_retries += 1
                        nudge("rate limit reset", check)
                    else:
                        nap = retry_at - clock.now()
            except API_ERRORS as err:
                say(True, f"ERROR {err!r}")
                return EXIT_ERROR

        remaining = ttl - elapsed()
        if remaining <= 0:
            say(True, f"TIMEOUT coderabbit still {last[0].lower() if last else 'pending'} after {ttl}s")
            return EXIT_TIMEOUT
        clock.sleep(min(nap if nap is not None else interval_for(elapsed()), remaining))


def report_findings(client, sha: str, pr: int | None, say, save) -> bool:
    try:
        pr = pr or client.open_pr(sha)
        threads = client.unresolved_threads(pr) if pr else []
    except API_ERRORS as err:
        say(False, f"findings: unavailable -- {err!r}")
        return False
    save("findings.json", threads)
    say(False, f"findings: {len(threads)} unresolved CodeRabbit thread(s), see findings.json")
    for thread in threads:
        mark = " (outdated)" if thread["outdated"] else ""
        where = f"{thread['path']}:{thread['line']}" if thread["line"] else thread["path"]
        say(False, f"  {where} {thread['severity']} {thread['title']}{mark}")
    return True


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ttl", type=int, required=True)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--no-trigger", action="store_true")
    parser.add_argument("--log-dir")
    args = parser.parse_args(argv)
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("wait-for-action.sh: not a git repository", file=sys.stderr)
        return EXIT_ERROR
    log_dir = Path(args.log_dir or f"/tmp/actions/coderabbit-{sha}")
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "poll.log").write_text("")
    start = time.time()

    def say(always: bool, line: str) -> None:
        stamped = f"[t={int(time.time() - start)}s] {line}"
        with (log_dir / "poll.log").open("a") as log:
            log.write(stamped + "\n")
        if always or not args.quiet:
            print(stamped, flush=True)

    def save(name: str, data) -> None:
        (log_dir / name).write_text(json.dumps(data, indent=2) + "\n")

    try:
        return watch(GhClient(), sha, args.ttl, Clock(), say, save, trigger=not args.no_trigger)
    except Exception as err:  # exit 1 means FAILED to callers, so never leak a traceback
        say(True, f"ERROR unexpected {err!r}")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
