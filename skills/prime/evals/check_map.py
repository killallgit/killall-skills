#!/usr/bin/env python3
"""Grade a prime eval run's map.md against the objective assertions for its eval, writing grading.json."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

Check = Callable[[str], tuple[bool, str]]


def mentions(pattern: str) -> Check:
    def check(text: str) -> tuple[bool, str]:
        match = re.search(pattern, text, re.I | re.M)
        return (True, line_of(text, match)) if match else (False, f"no match for /{pattern}/")
    return check


def mentions_all(*patterns: str) -> Check:
    def check(text: str) -> tuple[bool, str]:
        results = [(p, re.search(p, text, re.I | re.M)) for p in patterns]
        missing = [p for p, m in results if not m]
        if missing:
            return False, "missing: " + ", ".join(f"/{p}/" for p in missing)
        return True, " | ".join(line_of(text, m) for _, m in results)
    return check


def distinct_count(patterns: list[str], minimum: int) -> Check:
    def check(text: str) -> tuple[bool, str]:
        found = [p for p in patterns if re.search(p, text, re.I)]
        return len(found) >= minimum, f"{len(found)} of {len(patterns)} named: {', '.join(found)}"
    return check


def line_with_all(*patterns: str) -> Check:
    def check(text: str) -> tuple[bool, str]:
        for line in text.splitlines():
            if all(re.search(p, line, re.I) for p in patterns):
                return True, line.strip()[:200]
        return False, "no single line matches all of " + ", ".join(f"/{p}/" for p in patterns)
    return check


def terse(longest: int, average: int) -> Check:
    def check(text: str) -> tuple[bool, str]:
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
        if not lines:
            return False, "no content lines"
        worst = max(len(l) for l in lines)
        mean = sum(len(l) for l in lines) / len(lines)
        return worst <= longest and mean <= average, f"longest line {worst} chars (limit {longest}), average {mean:.0f} (limit {average})"
    return check


def max_lines(limit: int) -> Check:
    def check(text: str) -> tuple[bool, str]:
        count = len([l for l in text.splitlines() if l.strip()])
        return count <= limit, f"{count} non-empty lines (limit {limit})"
    return check


def line_of(text: str, match: re.Match | None) -> str:
    if not match:
        return ""
    start = text.rfind("\n", 0, match.start()) + 1
    end = text.find("\n", match.end())
    return text[start:end if end != -1 else None].strip()[:200]


PIPELINE_MODULES = [r"\bwalk\b", r"\bfingerprint\b", r"\bdiscover\b", r"\bdirsig\b", r"\barchive\b", r"\bexport\b", r"\breport\b", r"\bvolume\b", r"\bexcludes\b"]
WEB_API_DOMAINS = [r"\bclouds\b", r"\bbilling\b", r"\baccounts\b", r"\bauth\b", r"\busers\b", r"\bpops\b", r"\bresources\b", r"\bapi_keys\b", r"\bnotifications\b"]
WEB_API_SIBLINGS = [r"eyepop-actions", r"eyepop-sdk-python", r"eyepop-vercel", r"eyepop-charts", r"eyepop-billing", r"eyepop-pipeline", r"eyepop-testing", r"eyepop-instance\b", r"eyepop-developer-mcp", r"eyepop-sdk-node", r"eyepop-apps", r"eyepop-wiki", r"eyepop-cli\b", r"eyepop-security-audit", r"eyepop-agent-skills", r"eyepop-compute-admin"]
TOKEN_BUDGET = 50_000
MAP_EXPECTATIONS: list[tuple[str, Check]] = [
    ("map is a terse list: no content line over 200 characters, average under 120", terse(200, 120)),
]

ASSERTIONS: dict[str, list[tuple[str, Check]]] = {
    "scaffold-early-exit": [
        ("map is brief for a scaffold: at most 30 non-empty lines", max_lines(30)),
        ("names FastAPI and deepagents as the stack", mentions_all(r"fastapi", r"deepagents")),
        ("names the app factory (create_app / killall_router.app / app.py) as the entrypoint", mentions(r"create_app|killall_router\.app|\bapp\.py")),
        ("states that nothing has been committed yet", mentions(r"(no|zero|0) commits?\b|never (been )?committed|nothing (is |has been )?committed|no git history|unborn|no commit history|not (yet )?committed|initial commit (has not|hasn't)|nothing committed|uncommitted")),
        ("gives the test command (uv run pytest or task test)", mentions(r"uv run pytest|task test|\bpytest\b")),
        ("names the Taskfile or uv as the tooling", mentions(r"taskfile|\buv\b")),
    ],
    "small-python-cli": [
        ("names filescan/cli.py (filescan.cli:main) as the entrypoint", mentions(r"filescan/cli\.py|filescan\.cli:main|\bcli\.py")),
        ("identifies Click as the CLI framework", mentions(r"\bclick\b")),
        ("identifies db.py as the SQLite/database module", mentions(r"\bdb\.py")),
        ("flags that sqlite3 is also used in fingerprint.py or cli.py, contradicting CLAUDE.md's 'db.py only' claim", line_with_all(r"sqlite", r"fingerprint\.py|cli\.py")),
        ("gives the pytest command via uv", mentions(r"uv run( --extra dev)? pytest|uv run --extra dev")),
        ("names ruff as the linter", mentions(r"\bruff\b")),
        ("flags a working-tree gotcha: uncommitted changes, master.db in the root, or the second venv", mentions(r"uncommitted|master\.db|\.venv-visual|unstaged|modified files|dirty|working tree")),
        ("map is at most 60 non-empty lines", max_lines(60)),
        ("names at least three pipeline modules (walk, fingerprint, discover, dirsig, archive, export, report, volume, excludes)", distinct_count(PIPELINE_MODULES, 3)),
        ("notes frozen dataclasses or StrEnum in types.py", line_with_all(r"types\.py", r"frozen|dataclass|StrEnum")),
        ("names a script under scripts/ (01-move-extras.sh, 02-delete-recycle.sh, visual_dedup.py)", mentions(r"01-move-extras|02-delete-recycle|visual_dedup")),
        ("names xxhash or rich as a load-bearing library", mentions(r"xxhash|\brich\b")),
    ],
    "large-fastapi-with-siblings": [
        ("identifies app/main.py as where the FastAPI app is built", mentions(r"app/main\.py")),
        ("identifies Tortoise ORM with Aerich migrations", mentions_all(r"tortoise", r"aerich")),
        ("names db/models and db/migrations", mentions_all(r"db/models", r"db/migrations|\bmigrations/")),
        ("describes app/ as domain-organized, naming at least three domain packages", distinct_count(WEB_API_DOMAINS, 3)),
        ("gives a test command (task test / task check / pytest) and notes tests need MySQL", mentions_all(r"task test|task check|\bpytest\b|make test", r"mysql|3307")),
        ("names fastapi, tortoise and at least one of auth0/stripe/google-cloud as load-bearing", mentions_all(r"fastapi", r"tortoise", r"auth0|stripe|google[- .]cloud")),
        ("identifies eyepop-eyeballs as a sibling that is a direct dependency", line_with_all(r"eyepop-eyeballs", r"depend|requirement|git\+|pip|private")),
        ("names at least one more related sibling repo (actions, sdk, vercel, charts, billing, pipeline, testing, instance, developer-mcp, apps, wiki, cli)", distinct_count(WEB_API_SIBLINGS, 1)),
        ("flags the private dependency / GH_TOKEN requirement or the relaxed typecheck as a watch-out", mentions(r"GH_TOKEN|private (dep|package|repo|git)|gh auth|changed (files )?(vs|against|relative)|relaxed|only (checks|type-?checks) (files )?changed|diff against|files changed")),
        ("notes the gunicorn/uvicorn launch via scripts/entrypoint.sh", mentions(r"entrypoint\.sh|gunicorn")),
        ("notes startup jobs gated by disable_jobs / DISABLE_JOBS", mentions(r"disable_jobs|DISABLE_JOBS")),
        ("map is at most 70 non-empty lines", max_lines(70)),
        ("names a useful script beyond entrypoint.sh (localdev, test.sh, testdb, setup-db, seed, migrate, export_openapi, debug-local-db, start-db)", mentions(r"localdev\.sh|\btest\.sh|testdb\.sh|setup-db\.sh|seed\.sh|migrate\.sh|export_openapi|debug-local-db|start-db")),
        ("names config/settings.py as the settings hub", mentions(r"config/settings\.py")),
    ],
}


def spawned_subagents(transcript: Path) -> tuple[bool, str]:
    found = subprocess.run(["grep", "-o", '"type":"tool_use","id":"[^"]*","name":"Agent"', str(transcript)], capture_output=True, text=True).stdout
    count = len(found.splitlines())
    return count > 0, f"{count} Agent tool_use blocks in transcript"


def context_tokens(transcript: Path) -> tuple[int, int]:
    """Starting context and final context-plus-output, from the transcript's assistant usage blocks."""
    first = last = 0
    for line in transcript.read_text().splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("type") != "assistant":
            continue
        usage = (entry.get("message") or {}).get("usage") or {}
        if not usage:
            continue
        context = usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
        first = first or context
        last = context + usage.get("output_tokens", 0)
    return first, last


def run_expectations(transcript: Path | None) -> list[dict]:
    """The assertions every eval shares: no subagents, and the run stayed inside the token budget."""
    if transcript is None or not transcript.exists():
        return [{"text": text, "passed": False, "evidence": "no transcript given"} for text in ("spawned no subagents", f"prime added under {TOKEN_BUDGET // 1000}k tokens to the session (final context minus starting context)")]
    spawned, evidence = spawned_subagents(transcript)
    start, final = context_tokens(transcript)
    added = final - start
    return [
        {"text": "spawned no subagents", "passed": not spawned, "evidence": evidence},
        {"text": f"prime added under {TOKEN_BUDGET // 1000}k tokens to the session (final context minus starting context)", "passed": 0 < added < TOKEN_BUDGET, "evidence": f"{added:,} added ({start:,} at start -> {final:,} at the end)"},
    ]


def grade(run_dir: Path, transcript: Path | None) -> dict:
    metadata_path = next(c for c in (run_dir / "eval_metadata.json", run_dir.parent / "eval_metadata.json", run_dir.parent.parent / "eval_metadata.json") if c.exists())
    metadata = json.loads(metadata_path.read_text())
    map_path = run_dir / "outputs" / "map.md"
    text = map_path.read_text() if map_path.exists() else ""
    expectations = []
    for label, check in ASSERTIONS[metadata["eval_name"]] + MAP_EXPECTATIONS:
        passed, evidence = check(text) if text else (False, "map.md missing")
        expectations.append({"text": label, "passed": passed, "evidence": evidence})
    expectations += run_expectations(transcript)
    passed = sum(1 for e in expectations if e["passed"])
    result = {
        "expectations": expectations,
        "summary": {"passed": passed, "failed": len(expectations) - passed, "total": len(expectations), "pass_rate": round(passed / len(expectations), 3)},
        "execution_metrics": {"output_chars": len(text), "map_lines": len([l for l in text.splitlines() if l.strip()])},
    }
    if transcript is not None and transcript.exists():
        start, final = context_tokens(transcript)
        result["execution_metrics"].update({"starting_context_tokens": start, "final_context_tokens": final, "context_added_tokens": final - start})
    timing = run_dir / "timing.json"
    if timing.exists():
        result["execution_metrics"]["total_tool_calls"] = json.loads(timing.read_text()).get("tool_uses", 0)
    return result


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: check_map.py <run_dir> [transcript.jsonl]", file=sys.stderr)
        return 2
    run_dir = Path(argv[0])
    transcript = Path(argv[1]) if len(argv) > 1 else None
    result = grade(run_dir, transcript)
    (run_dir / "grading.json").write_text(json.dumps(result, indent=2))
    print(f"{run_dir.parent.name}/{run_dir.name}: {result['summary']['passed']}/{result['summary']['total']}")
    for e in result["expectations"]:
        print(f"  [{'PASS' if e['passed'] else 'FAIL'}] {e['text']} -- {e['evidence'][:110]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
