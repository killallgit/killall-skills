"""Parser checks for scripts/survey.py against small synthetic projects."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SURVEY = Path(__file__).resolve().parents[1] / "scripts" / "survey.py"
sys.path.insert(0, str(SURVEY.parent))
spec = importlib.util.spec_from_file_location("survey", SURVEY)
survey = importlib.util.module_from_spec(spec)
sys.modules["survey"] = survey
spec.loader.exec_module(survey)


def write(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


@pytest.fixture
def python_project(tmp_path: Path) -> Path:
    return write(tmp_path / "widget-api", {
        "pyproject.toml": '[project]\nname = "widget-api"\ndependencies = ["fastapi>=0.100", "httpx==0.27.0"]\n[project.optional-dependencies]\ndev = ["pytest", "ruff"]\n[project.scripts]\nwidget = "widget.cli:main"\n',
        "Taskfile.yml": 'version: "3"\ntasks:\n  test:\n    desc: Run tests\n    cmds:\n      - uv run pytest -m "not e2e"\n  typecheck:\n    cmd: |\n      git fetch origin main --quiet || true\n      uv run basedpyright\n  dev:\n    aliases: [run]\n    cmd: uv run uvicorn widget.app:create_app --factory\n  release:\n    cmds:\n      - |\n        echo one\n        echo two\n        echo three\n  seed:\n    cmd: ./scripts/seed.sh\n',
        "scripts/seed.sh": "#!/usr/bin/env bash\nset -euo pipefail\n# Seed the local database with demo widgets\npsql < seed.sql\n",
        "widget/__init__.py": "",
        "widget/app.py": "from fastapi import FastAPI\n\nfrom widget.settings import DEBUG\n\napp = FastAPI(debug=DEBUG)\n",
        "widget/cli.py": 'def main():\n    pass\n\n\nif __name__ == "__main__":\n    main()\n',
        "widget/settings.py": "import sqlite3\n\nDEBUG = False\n",
        "tests/test_app.py": "def test_app():\n    assert True\n",
        "README.md": "# widget\n",
    })


def test_requirement_names_keep_the_package_before_the_specifier() -> None:
    # Asserts the name survives version pins, extras, and the http-prefixed httpx trap.
    assert survey.requirement_name("httpx==0.27.0") == "httpx"
    assert survey.requirement_name("fastapi[all]>=0.100; python_version>'3.9'") == "fastapi"
    assert survey.requirement_name("eyeballs @ git+https://github.com/org/eyeballs.git@abc#subdirectory=python") == "eyeballs"
    assert survey.requirement_name("eyepop-eyeballs[fastapi] @ git+https://github.com/org/eyeballs.git@abc") == "eyepop-eyeballs"
    assert survey.requirement_name("git+https://github.com/org/thing.git@v1") == "thing"


def test_go_direct_deps_skip_indirect_modules_and_drop_the_host() -> None:
    # Asserts only direct requirements are listed, host-stripped.
    text = "module example.com/svc\n\nrequire (\n\tgithub.com/gin-gonic/gin v1.9.1\n\tgolang.org/x/sync v0.3.0 // indirect\n)\nrequire github.com/spf13/cobra v1.8.0\n"
    assert survey.go_direct_deps(text) == ["gin-gonic/gin", "spf13/cobra"]


def test_taskfile_commands_prefer_the_first_command_over_the_description(python_project: Path) -> None:
    # Asserts scalar cmd, cmds lists, and multi-line blocks each yield a runnable command, and aliases are ignored.
    manifests = survey.parse_manifest(survey.discover(python_project), "Taskfile.yml")
    commands = {name: cmd for _, name, cmd in manifests.commands}
    assert commands == {
        "test": 'uv run pytest -m "not e2e"',
        "typecheck": "git fetch origin main --quiet || true ; uv run basedpyright",
        "release": "echo one ; echo two ... (multi-line)",
        "dev": "uv run uvicorn widget.app:create_app --factory",
        "seed": "./scripts/seed.sh",
    }


def test_pyproject_yields_runtime_and_dev_dependencies_and_script_entrypoints(python_project: Path) -> None:
    # Asserts dependency names are split by group and the console script appears as an entrypoint.
    manifests = survey.parse_manifest(survey.discover(python_project), "pyproject.toml")
    assert manifests.runtime == ("fastapi", "httpx")
    assert manifests.dev == ("pytest", "ruff")
    assert manifests.entrypoints == ("pyproject scripts: widget = widget.cli:main",)


def test_tier_boundaries() -> None:
    # Asserts the empty/small/large thresholds.
    assert survey.tier_for(3, 50) == "empty"
    assert survey.tier_for(20, 3000) == "small"
    assert survey.tier_for(20, 20000) == "large"
    assert survey.tier_for(200, 3000) == "large"


def test_survey_of_a_non_git_directory_reports_markers_tests_and_no_repository(python_project: Path) -> None:
    # Asserts the full survey runs without git and finds the FastAPI marker, the main guard, and the test file.
    output = subprocess.run(["python3", str(SURVEY), str(python_project)], capture_output=True, text=True, check=True).stdout
    assert "git: not a repository" in output
    assert "FastAPI(: widget/app.py" in output
    assert "__main__ guard: widget/cli.py" in output
    assert "tests: 1 files -> tests/ 1" in output
    assert "commands (5 declared" in output


def test_survey_lists_scripts_with_their_doc_line_and_caller(python_project: Path) -> None:
    # Asserts a script shows its first real comment and the declared command that runs it.
    output = subprocess.run(["python3", str(SURVEY), str(python_project)], capture_output=True, text=True, check=True).stdout
    assert "scripts/seed.sh — Seed the local database with demo widgets (used by task seed)" in output


def test_survey_counts_libraries_by_importing_file_and_flags_unused_declarations(python_project: Path) -> None:
    # Asserts import counts use the declared names, the hub is the module others import, and an unimported runtime dependency is called out.
    output = subprocess.run(["python3", str(SURVEY), str(python_project)], capture_output=True, text=True, check=True).stdout
    assert "libraries in use (4 non-test files; files importing each): fastapi 1" in output
    assert "internal hubs (files importing each): widget/settings.py 1" in output
    assert "declared runtime, never imported: httpx" in output
    assert "stdlib signals (files): sqlite3 1 (widget/settings.py)" in output


def test_entrypoint_targets_put_the_declared_script_target_first(python_project: Path) -> None:
    # Asserts the pyproject console script's module outranks framework markers and main guards.
    project = survey.discover(python_project)
    manifests = survey.merge(survey.parse_manifest(project, rel) for rel in survey.manifest_paths(project.files))
    resolver = survey.Resolver.build(project.files, manifests.runtime + manifests.dev)
    sources = [f for f in project.files if survey.is_source(f)]
    scan = survey.scan_sources(project, sources, resolver)
    assert survey.entrypoint_targets(manifests, scan, sources, resolver)[:2] == ["widget/cli.py", "widget/app.py"]


def test_survey_of_a_bare_repository_is_the_empty_tier(tmp_path: Path) -> None:
    # Asserts a repository holding only a README stops at the empty tier with its file list.
    root = write(tmp_path / "bare", {"README.md": "# new\n"})
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    output = subprocess.run(["python3", str(SURVEY), str(root)], capture_output=True, text=True, check=True).stdout
    assert "tier: empty" in output
    assert "files: 1 total -> README.md" in output
    assert "layout:" not in output


def test_git_state_counts_an_unstaged_first_line_as_modified_not_staged(tmp_path: Path) -> None:
    # Asserts the leading space of the first porcelain line survives, so " M" is modified and nothing is staged.
    root = write(tmp_path / "repo", {"a.py": "x = 1\n", "b.py": "y = 2\n"})
    git = lambda *args: subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    git("init", "-q")
    git("-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init")
    (root / "a.py").write_text("x = 2\n")
    (root / "c.py").write_text("z = 3\n")
    state = survey.git_state(root)
    assert (state.staged, state.modified, state.untracked) == (0, 1, ("c.py",))
    assert state.commits == 1
