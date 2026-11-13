#!/usr/bin/env python3
"""Read-only discovery of observable PR activity. Never requests a review."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from coderabbit import GhError, classify, interval_for

GOOD = {"success", "neutral", "skipped"}


def bot(login):
    """Known bot identities plus GitHub's general bot suffix."""
    login = login or ""
    return login.endswith("[bot]") or login.lower() in {"coderabbitai", "copilot", "copilot-pull-request-reviewer", "github-copilot"}


class Client:
    def __init__(self, repo=None):
        self.repo = repo
        self.deadline = 0

    def gh(self, *args):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        env = dict(os.environ, GH_PROMPT_DISABLED="1")
        if self.repo:
            env["GH_REPO"] = self.repo
        try:
            result = subprocess.run(["gh", *args], capture_output=True, text=True,
                                    timeout=min(30, remaining), env=env)
        except subprocess.TimeoutExpired as err:
            if time.monotonic() >= self.deadline:
                raise TimeoutError from err
            raise GhError("GitHub request timed out") from err
        if result.returncode:
            raise GhError(result.stderr.strip() or "GitHub request failed")
        return json.loads(result.stdout)

    def pages(self, endpoint):
        # gh pagination handles check/status/comment collections beyond page one.
        return self.gh("api", "--paginate", "--slurp", endpoint)

    def snapshot(self, pr):
        head = self.gh("pr", "view", *([str(pr)] if pr else []), "--json",
                       "number,url,headRefOid,reviewRequests")
        sha, number = head["headRefOid"], head["number"]
        root = "repos/{owner}/{repo}"
        checks = [c for page in self.pages(f"{root}/commits/{sha}/check-runs?per_page=100") for c in page["check_runs"]]
        statuses = [s for page in self.pages(f"{root}/commits/{sha}/statuses?per_page=100") for s in page]
        workflows = [r for page in self.pages(f"{root}/actions/runs?head_sha={sha}&per_page=100") for r in page["workflow_runs"]]
        reviews = [r for page in self.pages(f"{root}/pulls/{number}/reviews?per_page=100") for r in page]
        comments = [c for page in self.pages(f"{root}/issues/{number}/comments?per_page=100") for c in page]
        # Re-read to reject snapshots straddling a push.
        latest = self.gh("pr", "view", str(number), "--json", "headRefOid")
        if latest["headRefOid"] != sha:
            return None
        return dict(head=head, checks=checks, statuses=statuses, workflows=workflows,
                    reviews=reviews, comments=comments)


def latest_by(rows, key):
    result = {}
    for row in rows:
        k = key(row)
        if k not in result or row.get("id", 0) > result[k].get("id", 0):
            result[k] = row
    return list(result.values())


def summarize(snapshot):
    head = snapshot["head"]
    pending, failed, observations = [], [], []
    checks = latest_by(snapshot["checks"], lambda c: ((c.get("app") or {}).get("id"), c["name"]))
    for c in checks:
        name = c["name"]
        if name == "CodeRabbit":
            verdict = classify(c, None)
            if verdict.kind in {"SKIPPED", "RATE_LIMITED"}:
                observations.append(f"CodeRabbit: {verdict.kind.lower()} ({verdict.detail})")
                continue
        if c["status"] != "completed":
            pending.append(f"{name}: {c['status']}")
        elif c.get("conclusion") not in GOOD:
            failed.append(f"{name}: {c.get('conclusion') or 'unknown conclusion'}")
        else:
            observations.append(f"{name}: {c['conclusion']}")
    for s in latest_by(snapshot["statuses"], lambda s: s["context"]):
        if s["context"] == "CodeRabbit":
            verdict = classify(None, s)
            if verdict.kind in {"SKIPPED", "RATE_LIMITED"}:
                observations.append(f"CodeRabbit: {verdict.kind.lower()} ({verdict.detail})")
                continue
        if s["state"] == "pending":
            pending.append(f"{s['context']}: pending")
        elif s["state"] != "success":
            failed.append(f"{s['context']}: {s['state']}")
        else:
            observations.append(f"{s['context']}: success")
    # Workflows may be queued before their first job/check exists. Only the
    # newest run of each workflow counts; old failed runs are not new failures.
    for r in latest_by(snapshot["workflows"], lambda r: (r.get("workflow_id"), r.get("event"))):
        if r["status"] != "completed":
            pending.append(f"workflow {r['name']}: {r['status']}")
        elif r.get("conclusion") not in GOOD:
            failed.append(f"workflow {r['name']}: {r.get('conclusion') or 'unknown conclusion'}")
        else:
            observations.append(f"workflow {r['name']}: {r['conclusion']}")
    reviews = [r for r in snapshot["reviews"] if bot((r.get("user") or {}).get("login"))]
    current = {r["user"]["login"] for r in reviews if r.get("commit_id") == head["headRefOid"] and r.get("submitted_at")}
    for login in sorted(current):
        observations.append(f"{login}: review submitted for current head (not a findings verdict)")
    for login in sorted({r["user"]["login"] for r in reviews} - current):
        observations.append(f"{login}: older-head review only; current activity unknown")
    for request in head.get("reviewRequests", []):
        login = request.get("login", "")
        if bot(login) and login not in current:
            observations.append(f"{login}: requested, start unconfirmed")
    # A comment alone cannot establish which commit was reviewed, nor prove a
    # reviewer is still running. Keep only each bot's latest informational signal.
    for c in latest_by(snapshot["comments"], lambda c: (c.get("user") or {}).get("login")):
        login = (c.get("user") or {}).get("login")
        if not bot(login) or login in current:
            continue
        body = c.get("body", "").lower()
        if "rate limit" in body:
            state = "rate-limit notice"
        elif "skip" in body or "paused" in body:
            state = "skip/pause notice"
        else:
            state = "comment observed"
        observations.append(f"{login}: {state}; current-head activity unconfirmed")
    return dict(head=head["headRefOid"], url=head["url"], pending=sorted(set(pending)),
                failed=sorted(set(failed)), observations=sorted(set(observations)))


def watch(client, pr, ttl, log_dir, quiet=False, fail_fast=True, clock=time, settle=10, interval=None):
    start = clock.monotonic()
    client.deadline = start + ttl
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "poll.log").write_text("")
    last = None
    stable_at = start
    errors = 0
    report = None

    def emit(kind, text):
        line = f"[t={int(clock.monotonic() - start)}s] {kind} {text}"
        with (log_dir / "poll.log").open("a") as f:
            f.write(line + "\n")
        if not quiet or kind != "PENDING":
            print(line, flush=True)

    while clock.monotonic() < client.deadline:
        try:
            snapshot = client.snapshot(pr)
            if snapshot is None:
                last = None
                stable_at = clock.monotonic()
                emit("PENDING", "PR head changed; rediscovering")
            else:
                report = summarize(snapshot)
                (log_dir / "activity.json").write_text(json.dumps(snapshot, indent=2) + "\n")
                (log_dir / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
                errors = 0
                key = json.dumps(report, sort_keys=True)
                if key != last:
                    last, stable_at = key, clock.monotonic()
                    emit("PENDING", "; ".join(report["pending"] + report["failed"] + report["observations"]) or "no observable activity")
                if report["failed"] and (fail_fast or not report["pending"]):
                    emit("FAILED", "; ".join(report["failed"]))
                    return 1
                if not report["pending"] and clock.monotonic() - stable_at >= settle:
                    # Unknown/unacknowledged reviewers are reported, never promoted
                    # to running work or to a successful independent review.
                    for observation in report["observations"]:
                        emit("OBSERVED", observation)
                    emit("DONE", f"no observable work pending; not a merge/review approval {report['url']}")
                    return 0
        except TimeoutError:
            break
        except (GhError, ValueError, KeyError, TypeError, OSError) as err:
            errors += 1
            last = None
            stable_at = clock.monotonic()
            emit("PENDING", f"discovery error: {err}")
            if errors >= 3:
                emit("ERROR", f"discovery failed: {err}")
                return 3
        remaining = client.deadline - clock.monotonic()
        if remaining > 0:
            nap = interval if interval is not None else (
                interval_for(int(clock.monotonic() - start)) if report and report["pending"] else 5)
            clock.sleep(min(nap, remaining))
    emit("TIMEOUT", f"activity not settled within {ttl}s; see {log_dir}")
    return 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr")
    parser.add_argument("--repo")
    parser.add_argument("--ttl", type=int, default=900)
    parser.add_argument("--log-dir")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--no-fail-fast", action="store_true")
    args = parser.parse_args()
    if args.ttl <= 0:
        parser.error("--ttl must be positive")
    return watch(Client(args.repo), args.pr, args.ttl,
                 args.log_dir or f"/tmp/actions/activity-{args.pr or 'current'}", args.quiet,
                 not args.no_fail_fast)


if __name__ == "__main__":
    raise SystemExit(main())
