#!/usr/bin/env python3
"""Read-only discovery of observable PR activity. Never requests a review."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

GOOD = {"success", "neutral", "skipped"}


class GhError(Exception):
    pass


def duration(value):
    match = re.fullmatch(r"([1-9]\d*)([smh]?)", value)
    if not match:
        raise argparse.ArgumentTypeError("use a positive duration such as 45s, 15m, or 1h")
    return int(match[1]) * {"": 1, "s": 1, "m": 60, "h": 3600}[match[2]]


def identity(login):
    return (login or "").lower().removesuffix("[bot]")


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
    workflows = snapshot["workflows"]
    workflow_key = lambda r: (r.get("workflow_id"), r.get("event"))
    newest_workflows = {workflow_key(r): r for r in latest_by(workflows, workflow_key)}
    # A completed old run's checks must not fail a replacement run before its
    # own checks register. Suppress only when suite metadata proves the link.
    superseded_suites = {
        r["check_suite_id"] for r in workflows
        if r["status"] == "completed" and r.get("check_suite_id") is not None
        and r["id"] != newest_workflows[workflow_key(r)]["id"]
    }
    # Job names are not unique across workflows/apps. Only supersede checks
    # within one suite; missing suite metadata must not hide a distinct check.
    checks = latest_by(snapshot["checks"], lambda c: (
        (c.get("app") or {}).get("id"),
        (c.get("check_suite") or {}).get("id", ("check", c["id"])), c["name"]))
    for c in checks:
        if c["status"] == "completed" and (c.get("check_suite") or {}).get("id") in superseded_suites:
            continue
        name = c["name"]
        if c["status"] != "completed":
            pending.append(f"{name}: {c['status']}")
        elif c.get("conclusion") not in GOOD:
            failed.append(f"{name}: {c.get('conclusion') or 'unknown conclusion'}")
        else:
            title = (c.get("output") or {}).get("title")
            observations.append(f"{name}: {c['conclusion']}" + (f" ({title})" if title else ""))
    for s in latest_by(snapshot["statuses"], lambda s: s["context"]):
        if s["state"] == "pending":
            pending.append(f"{s['context']}: pending")
        elif s["state"] != "success":
            failed.append(f"{s['context']}: {s['state']}")
        else:
            description = s.get("description")
            observations.append(f"{s['context']}: success" + (f" ({description})" if description else ""))
    # Workflows may be queued before their first job/check exists. Retain every
    # incomplete run, even when a newer run has finished. Only completed results
    # can be superseded by a newer run of the same workflow/event.
    for r in workflows:
        if r["status"] == "completed" and r["id"] != newest_workflows[workflow_key(r)]["id"]:
            continue
        if r["status"] != "completed":
            pending.append(f"workflow {r['name']}: {r['status']}")
        elif r.get("conclusion") not in GOOD:
            failed.append(f"workflow {r['name']}: {r.get('conclusion') or 'unknown conclusion'}")
        else:
            observations.append(f"workflow {r['name']}: {r['conclusion']}")
    reviews = [r for r in snapshot["reviews"] if bot((r.get("user") or {}).get("login"))]
    current = {r["user"]["login"] for r in reviews if r.get("commit_id") == head["headRefOid"] and r.get("submitted_at")}
    current_identities = {identity(login) for login in current}
    for login in sorted(current):
        observations.append(f"{login}: review submitted for current head (not a findings verdict)")
    for login in sorted({r["user"]["login"] for r in reviews if identity(r["user"]["login"]) not in current_identities}):
        observations.append(f"{login}: older-head review only; current activity unknown")
    for request in head.get("reviewRequests", []):
        login = request.get("login", "")
        if bot(login) and identity(login) not in current_identities:
            observations.append(f"{login}: requested, start unconfirmed")
    # A comment alone cannot establish which commit was reviewed, nor prove a
    # reviewer is still running. Keep only each bot's latest informational signal.
    for c in latest_by(snapshot["comments"], lambda c: (c.get("user") or {}).get("login")):
        login = (c.get("user") or {}).get("login")
        if not bot(login) or identity(login) in current_identities:
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
                observed=bool(checks or snapshot["statuses"] or snapshot["workflows"] or current),
                failed=sorted(set(failed)), observations=sorted(set(observations)))


def watch(client, pr, ttl, log_dir, clock=time, settle=10):
    start = clock.monotonic()
    client.deadline = start + ttl
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "poll.log").write_text("")
    last = None
    stable_at = start
    errors = 0

    def emit(kind, text):
        # Remote names/titles must not forge status lines or terminal controls.
        text = " ".join(str(text).split())
        text = "".join(char for char in text if char.isprintable())
        line = f"[t={int(clock.monotonic() - start)}s] {kind} {text}"
        with (log_dir / "poll.log").open("a") as f:
            f.write(line + "\n")
        print(line, flush=True)

    emit("ARTIFACTS", str(log_dir))
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
                if report["failed"]:
                    emit("FAILED", "; ".join(report["failed"]))
                    return 1
                if not report["pending"] and clock.monotonic() - stable_at >= settle:
                    # Unknown/unacknowledged reviewers are reported, never promoted
                    # to running work or to a successful independent review.
                    for observation in report["observations"]:
                        emit("OBSERVED", observation)
                    if not report["observed"]:
                        emit("NONE", f"no current-head execution or submitted bot review observed; work may not have registered yet {report['url']}")
                        return 5
                    emit("NOTE", "Late-registering work may still appear; enforce required checks/reviews separately")
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
            clock.sleep(min(5, remaining))
    emit("TIMEOUT", f"activity not settled within {ttl}s; see {log_dir}")
    return 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, help="PR number; defaults to the current branch's PR")
    parser.add_argument("--repo", help="OWNER/REPO; defaults to the current repository")
    parser.add_argument("--ttl", type=duration, default="15m", metavar="DURATION")
    parser.add_argument("--log-dir", help="artifact directory; defaults to a private temporary directory")
    args = parser.parse_args()
    if args.pr is not None and args.pr <= 0:
        parser.error("--pr must be positive")
    log_dir = args.log_dir
    if not log_dir:
        log_dir = tempfile.mkdtemp(prefix=f"activity-{args.pr or 'current'}-")
    return watch(Client(args.repo), args.pr, args.ttl, log_dir)


if __name__ == "__main__":
    raise SystemExit(main())
