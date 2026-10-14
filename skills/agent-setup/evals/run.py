#!/usr/bin/env python3
"""Run each case in evals.json against a fresh fixture repository and report PASS or FAIL."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

EVALS = Path(__file__).resolve().parent
SKILL = EVALS.parent
FIXTURES = EVALS / "fixtures"
RENDERER = SKILL / "scripts" / "render_agents.py"
sys.path.insert(0, str(FIXTURES))

from make_repo import build  # noqa: E402

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


def render(repo: Path, args: list[str], vars_path: Path) -> subprocess.CompletedProcess[str]:
    expanded = (arg.replace("{vars}", str(vars_path)).replace("{fixtures}", str(FIXTURES)) for arg in args)
    return subprocess.run([sys.executable, str(RENDERER), "--dest", str(repo), *expanded], capture_output=True, text=True)


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


def toml_parses(text: str) -> bool:
    try:
        import tomllib
    except ImportError:
        return True
    tomllib.loads(text)
    return True


def word_count(paths: list[Path]) -> int:
    return sum(len(path.read_text(encoding="utf-8").split()) for path in paths)


def check_budget(budget: dict) -> list[str]:
    words = word_count([SKILL / "SKILL.md", *sorted((SKILL / "templates").glob("*.tmpl.md"))])
    lines = len(RENDERER.read_text(encoding="utf-8").splitlines())
    print(f"  text-budget: {words} words, renderer {lines} lines")
    failures = []
    if words > budget["max_words"]:
        failures.append(f"{words} words > {budget['max_words']}")
    if lines > budget["max_renderer_lines"]:
        failures.append(f"renderer {lines} lines > {budget['max_renderer_lines']}")
    pattern = re.compile(budget["forbidden"], re.I)
    for path in sorted(SKILL.rglob("*")):
        if path.is_file() and "evals" not in path.relative_to(SKILL).parts and path.suffix in {".md", ".py", ".yaml"}:
            if pattern.search(path.read_text(encoding="utf-8")):
                failures.append(f"forbidden name in {path.relative_to(SKILL)}")
    return failures


def assertions(case: dict, result: subprocess.CompletedProcess[str], before: Tree, after: Tree) -> list[str]:
    failures = []
    expect_exit = case.get("expect_exit", 0)
    if (expect_exit == "nonzero" and result.returncode == 0) or (expect_exit != "nonzero" and result.returncode != expect_exit):
        failures.append(f"exit {result.returncode}, expected {expect_exit}: {result.stderr.strip()[-200:]}")
    actual = changes(before, after)
    for kind, expected in case.get("expect_changes", {}).items():
        if actual[kind] != sorted(expected):
            failures.append(f"{kind} {actual[kind]} != {sorted(expected)}")
    for path in case.get("expect_files", []):
        if path not in after:
            failures.append(f"missing {path}")
    for path in case.get("expect_absent", []):
        if path in after:
            failures.append(f"present {path}")
    for path in case.get("expect_unchanged", []):
        if before.get(path) != after.get(path):
            failures.append(f"changed {path}")
    for path, fields in case.get("expect_metadata", {}).items():
        found = metadata(path, after[path]) if path in after else {}
        for key, value in fields.items():
            if value is None and key in found:
                failures.append(f"{path}: unexpected {key}")
            elif value is not None and unquote(found.get(key)) != value:
                failures.append(f"{path}: {key}={found.get(key)!r}, expected {value!r}")
    for path, prefix in case.get("expect_startswith", {}).items():
        if not after.get(path, "").startswith(prefix):
            failures.append(f"{path} does not start with {prefix!r}")
    for path, suffix in case.get("expect_endswith", {}).items():
        if not after.get(path, "").endswith(suffix):
            failures.append(f"{path} does not end with {suffix!r}")
    for path in case.get("expect_toml", []):
        try:
            toml_parses(after[path])
        except Exception as error:  # tomllib.TOMLDecodeError, only importable on 3.11+
            failures.append(f"{path} is not valid TOML: {error}")
    written = [path for path in actual["added"] + actual["modified"]]
    for pattern in case.get("expect_no_match", []):
        regex = re.compile(pattern, re.I | re.M)
        failures += [f"{path} matches {pattern!r}" for path in written if regex.search(after[path])]
    for needle in case.get("expect_output", []):
        if needle not in result.stdout + result.stderr:
            failures.append(f"output lacks {needle!r}")
    return failures


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
        for name, content in case.get("files_after_setup", {}).items():
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text(content, encoding="utf-8")
        before = snapshot(repo)
        result = render(repo, case["args"], vars_path)
        return assertions(case, result, before, snapshot(repo))


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
