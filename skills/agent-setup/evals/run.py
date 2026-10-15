"""Run each case in evals.json against a fresh fixture repository and report PASS or FAIL."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

EVALS = Path(__file__).resolve().parent
SKILL = EVALS.parent
FIXTURES = EVALS / "fixtures"
RENDERER = SKILL / "scripts" / "render_agents.py"
sys.path.insert(0, str(FIXTURES))

from make_repo import build

Tree = dict[str, str]


def snapshot(repo: Path) -> Tree:
    return {
        str(path.relative_to(repo)): path.read_text(encoding="utf-8")
        for path in sorted(repo.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    }


def write_vars(folder: Path, overrides: dict[str, str]) -> Path:
    values = {**json.loads((FIXTURES / "vars.json").read_text(encoding="utf-8")), **overrides}
    path = folder / "vars.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    return path


def render(repo: Path, args: list[str], vars_path: Path, config_home: Path | None = None) -> subprocess.CompletedProcess[str]:
    expanded = (arg.replace("{vars}", str(vars_path)).replace("{fixtures}", str(FIXTURES)) for arg in args)
    env = {**os.environ, "XDG_CONFIG_HOME": str(config_home or repo.parent / "config")}
    return subprocess.run([sys.executable, str(RENDERER), "--dest", str(repo), *expanded], check=False, capture_output=True, text=True, env=env)


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    block = text[4 : text.index("\n---\n", 4)]
    return {key.strip(): value.strip() for key, _, value in (line.partition(":") for line in block.splitlines())}


def toml_keys(text: str) -> dict[str, str]:
    """Single-line `key = value` pairs only; multi-line literals are reported by their first line."""
    pairs = (line.partition("=") for line in text.splitlines() if re.match(r"^[a-z_]+ = ", line))
    return {key.strip(): value.strip() for key, _, value in pairs}


def metadata(path: str, text: str) -> dict:
    if path.endswith(".json"):
        return json.loads(text)
    if path.endswith(".toml"):
        return toml_keys(text)
    return frontmatter(text)


def unquote(value):
    return json.loads(value) if isinstance(value, str) and value[:1] == '"' else value


def changes(before: Tree, after: Tree) -> dict[str, list[str]]:
    return {
        "added": sorted(set(after) - set(before)),
        "removed": sorted(set(before) - set(after)),
        "modified": sorted(path for path in set(before) & set(after) if before[path] != after[path]),
    }


def toml_error(text: str) -> str | None:
    """Returns None on Python before 3.11, which has no tomllib, so expect_toml passes silently there."""
    try:
        import tomllib
    except ImportError:
        return None
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        return str(error)
    return None


def word_count(paths: list[Path]) -> int:
    return sum(len(path.read_text(encoding="utf-8").split()) for path in paths)


def check_budget(budget: dict) -> list[str]:
    words = word_count([SKILL / "SKILL.md", *sorted((SKILL / "templates").glob("*.md"))])
    lines = len(RENDERER.read_text(encoding="utf-8").splitlines())
    print(f"  text-budget: {words} words, renderer {lines} lines")
    failures = []
    if words > budget["max_words"]:
        failures.append(f"{words} words > {budget['max_words']}")
    if lines > budget["max_renderer_lines"]:
        failures.append(f"renderer {lines} lines > {budget['max_renderer_lines']}")
    pattern = re.compile(budget["forbidden"], re.IGNORECASE)
    for path in sorted(SKILL.rglob("*")):
        checked = path.is_file() and "evals" not in path.relative_to(SKILL).parts and path.suffix in {".md", ".py", ".yaml"}
        if checked and pattern.search(path.read_text(encoding="utf-8")):
            failures.append(f"forbidden name in {path.relative_to(SKILL)}")
    return failures


class Outcome(NamedTuple):
    result: subprocess.CompletedProcess[str]
    before: Tree
    after: Tree


def exit_code(case: dict, outcome: Outcome) -> list[str]:
    expected, actual = case.get("expect_exit", 0), outcome.result.returncode
    if (actual != 0) if expected == "nonzero" else (actual == expected):
        return []
    return [f"exit {actual}, expected {expected}: {outcome.result.stderr.strip()[-200:]}"]


def changed_paths(case: dict, outcome: Outcome) -> list[str]:
    actual = changes(outcome.before, outcome.after)
    expected = case.get("expect_changes", {}).items()
    return [f"{kind} {actual[kind]} != {sorted(paths)}" for kind, paths in expected if actual[kind] != sorted(paths)]


def present_files(case: dict, outcome: Outcome) -> list[str]:
    return [f"missing {path}" for path in case.get("expect_files", []) if path not in outcome.after]


def absent_files(case: dict, outcome: Outcome) -> list[str]:
    return [f"present {path}" for path in case.get("expect_absent", []) if path in outcome.after]


def unchanged_files(case: dict, outcome: Outcome) -> list[str]:
    paths = case.get("expect_unchanged", [])
    return [f"changed {path}" for path in paths if outcome.before.get(path) != outcome.after.get(path)]


def metadata_fields(case: dict, outcome: Outcome) -> list[str]:
    failures = []
    for path, fields in case.get("expect_metadata", {}).items():
        found = metadata(path, outcome.after[path]) if path in outcome.after else {}
        for key, value in fields.items():
            if value is None and key in found:
                failures.append(f"{path}: unexpected {key}")
            elif value is not None and unquote(found.get(key)) != value:
                failures.append(f"{path}: {key}={found.get(key)!r}, expected {value!r}")
    return failures


def file_contents(case: dict, outcome: Outcome) -> list[str]:
    expected = case.get("expect_content", {}).items()
    return [f"{path} content {outcome.after.get(path)!r} != {text!r}" for path, text in expected if outcome.after.get(path) != text]


def file_prefixes(case: dict, outcome: Outcome) -> list[str]:
    expected = case.get("expect_startswith", {}).items()
    return [f"{path} does not start with {text!r}" for path, text in expected if not outcome.after.get(path, "").startswith(text)]


def file_suffixes(case: dict, outcome: Outcome) -> list[str]:
    expected = case.get("expect_endswith", {}).items()
    return [f"{path} does not end with {text!r}" for path, text in expected if not outcome.after.get(path, "").endswith(text)]


def valid_toml(case: dict, outcome: Outcome) -> list[str]:
    errors = ((path, toml_error(outcome.after[path])) for path in case.get("expect_toml", []))
    return [f"{path} is not valid TOML: {error}" for path, error in errors if error]


def forbidden_patterns(case: dict, outcome: Outcome) -> list[str]:
    actual = changes(outcome.before, outcome.after)
    written = actual["added"] + actual["modified"]
    failures = []
    for pattern in case.get("expect_no_match", []):
        regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        failures += [f"{path} matches {pattern!r}" for path in written if regex.search(outcome.after[path])]
    return failures


def output_mentions(case: dict, outcome: Outcome) -> list[str]:
    output = outcome.result.stdout + outcome.result.stderr
    return [f"output lacks {needle!r}" for needle in case.get("expect_output", []) if needle not in output]


CHECKS = (
    exit_code,
    changed_paths,
    present_files,
    absent_files,
    unchanged_files,
    metadata_fields,
    file_contents,
    file_prefixes,
    file_suffixes,
    valid_toml,
    forbidden_patterns,
    output_mentions,
)


def run_case(case: dict) -> list[str]:
    if "text_budget" in case:
        return check_budget(case["text_budget"])
    with tempfile.TemporaryDirectory() as tmp:
        repo = build(Path(tmp) / "repo", case.get("files", {}), case.get("previous"))
        vars_path = write_vars(Path(tmp), case.get("vars", {}))
        for setup in case.get("setup", []):
            completed = render(repo, setup, vars_path)
            if completed.returncode:
                return [f"setup failed: {completed.stderr.strip()}"]
        before = snapshot(repo)
        result = render(repo, case["args"], vars_path)
        outcome = Outcome(result, before, snapshot(repo))
        return [failure for check in CHECKS for failure in check(case, outcome)]


def main() -> None:
    cases = json.loads((EVALS / "evals.json").read_text(encoding="utf-8"))["cases"]
    only = set(sys.argv[1:])
    failed = 0
    for case in cases:
        if only and case["id"] not in only:
            continue
        failures = run_case(case)
        failed += bool(failures)
        print(("FAIL " if failures else "PASS ") + case["id"])
        for failure in failures:
            print(f"  {failure}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
