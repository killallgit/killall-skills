#!/usr/bin/env python3
"""Print a compact inventory of a project so an agent can map it without reading all of it."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Iterable

from source_analysis import CodeFacts, FileFacts, Resolver, aggregate, analyze, doc_line, is_script_path, is_tool, normalize, outline

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None

IGNORED_DIRS = frozenset({
    ".git", "node_modules", "venv", "__pycache__", "dist", "build", "target", ".next", ".nuxt",
    ".svelte-kit", "coverage", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".nox",
    ".idea", ".vscode", "vendor", "Pods", "DerivedData", ".terraform", ".cache", "site-packages",
    ".gradle", ".dart_tool", ".turbo", ".parcel-cache", ".serverless",
})

LANGUAGES = {
    "py": "python", "pyi": "python", "ts": "typescript", "tsx": "typescript", "js": "javascript",
    "jsx": "javascript", "mjs": "javascript", "cjs": "javascript", "vue": "vue", "svelte": "svelte",
    "go": "go", "rs": "rust", "java": "java", "kt": "kotlin", "kts": "kotlin", "swift": "swift",
    "rb": "ruby", "php": "php", "cs": "csharp", "c": "c", "h": "c", "cpp": "cpp", "cc": "cpp",
    "hpp": "cpp", "scala": "scala", "ex": "elixir", "exs": "elixir", "erl": "erlang",
    "hs": "haskell", "ml": "ocaml", "clj": "clojure", "dart": "dart", "lua": "lua", "sh": "shell",
    "bash": "shell", "zsh": "shell", "sql": "sql", "r": "r", "jl": "julia", "m": "objc",
    "mm": "objc", "gd": "gdscript", "proto": "protobuf", "graphql": "graphql", "tf": "terraform",
    "hcl": "hcl", "cue": "cue", "zig": "zig", "nim": "nim", "fbs": "flatbuffers",
}

MANIFEST_NAMES = (
    "package.json", "pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json", "tsconfig.json",
    "pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "go.mod", "go.work", "Cargo.toml",
    "Gemfile", "pom.xml", "build.gradle", "build.gradle.kts", "composer.json", "mix.exs",
    "Package.swift", "pubspec.yaml", "CMakeLists.txt", "Makefile", "justfile", "Justfile",
    "Taskfile.yml", "Taskfile.yaml", "docker-compose.yml", "docker-compose.yaml", "compose.yml",
    "compose.yaml", "Chart.yaml", "Procfile", "fly.toml", "vercel.json", "netlify.toml",
    "serverless.yml", "devbox.json", "flake.nix", ".tool-versions", ".python-version", ".nvmrc",
    ".node-version", "project.godot", "app.json", "eas.json", "Tiltfile", "skaffold.yaml",
    "docker-bake.hcl", "Brewfile", "pytest.ini", "tox.ini", "noxfile.py", "jest.config.js",
    "jest.config.ts", "vitest.config.ts", "vitest.config.js", "playwright.config.ts",
    "cypress.config.ts", "cypress.config.js", ".mocharc.yml", ".mocharc.json", "diesel.toml",
    "alembic.ini", "prisma/schema.prisma", "drizzle.config.ts", "sqlx-data.json",
)

LOCKFILES = {
    "uv.lock": "uv", "poetry.lock": "poetry", "Pipfile.lock": "pipenv", "pdm.lock": "pdm",
    "pnpm-lock.yaml": "pnpm", "yarn.lock": "yarn", "bun.lock": "bun", "bun.lockb": "bun",
    "package-lock.json": "npm", "Cargo.lock": "cargo", "go.sum": "go modules",
    "Gemfile.lock": "bundler", "composer.lock": "composer", "mix.lock": "mix", "Podfile.lock": "cocoapods",
}

FRAMEWORK_MARKERS = (
    "FastAPI(", "Flask(", "typer.Typer(", "click.group(", "@click.command", "Celery(", "DJANGO_SETTINGS_MODULE",
    "express()", "new Hono(", "NestFactory.create", "app.listen(", "fastify(", "createServer(",
    "registerRootComponent(", "http.ListenAndServe", "gin.Default(", "gin.New(", "echo.New(",
    "fiber.New(", "grpc.NewServer(", "cobra.Command{", "HttpServer::new", "axum::serve",
    "Router::new()", "#[derive(Parser", "#[tokio::main", "#[actix_web::main", "clap::Command",
)

MAIN_MARKERS = ("func main()", "fn main()", 'if __name__ == "__main__"', "if __name__ == '__main__'")

ENTRY_STEMS = frozenset({"main", "app", "index", "server", "cli", "manage", "wsgi", "asgi", "__main__", "lib", "mod", "_layout", "App"})

PRIORITY_COMMANDS = ("test", "lint", "check", "typecheck", "build", "dev", "start", "run", "fmt", "format", "migrate", "install", "e2e", "ci")

SCAN_CAP = 4000
SMALL_FILES = 40
SMALL_LINES = 8000


@dataclass(frozen=True)
class Limits:
    top_dirs: int = 18
    children: int = 12
    commands: int = 22
    dependencies: int = 60
    siblings: int = 12
    command_width: int = 100
    scripts: int = 12
    libraries: int = 14
    hubs: int = 8
    pattern_items: int = 8
    outlines: int = 3
    hub_outlines: int = 2
    outline_lines: int = 12

    @classmethod
    def unlimited(cls) -> "Limits":
        return cls(**{f.name: 10**6 for f in fields(cls)})


@dataclass(frozen=True)
class GitState:
    branch: str
    commits: int
    last: str
    staged: int
    modified: int
    untracked: tuple[str, ...]
    drift: tuple[str, ...]
    nested: tuple[str, ...]
    ignored: tuple[str, ...]


@dataclass(frozen=True)
class Project:
    root: Path
    is_git: bool
    files: tuple[str, ...]


@dataclass(frozen=True)
class SourceScan:
    lines: dict[str, int]
    markers: dict[str, list[str]]
    rust_test_blocks: int
    sampled: bool
    facts: CodeFacts
    per_file: dict[str, FileFacts]


@dataclass(frozen=True)
class Manifests:
    paths: tuple[str, ...]
    runtime: tuple[str, ...] = ()
    dev: tuple[str, ...] = ()
    commands: tuple[tuple[str, str, str], ...] = ()
    entrypoints: tuple[str, ...] = ()
    compose_services: tuple[str, ...] = ()
    workspace: str = ""


def run_git(root: Path, *args: str, strip: bool = True) -> str:
    try:
        completed = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip() if strip else completed.stdout


def is_ignored(rel: str) -> bool:
    parts = rel.split("/")[:-1]
    return any(p in IGNORED_DIRS or p.startswith(".venv") or p.endswith(".egg-info") for p in parts)


def walk(root: Path) -> Iterable[str]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not is_ignored(f"{d}/x"))
        for name in filenames:
            yield (Path(dirpath) / name).relative_to(root).as_posix()


def discover(root: Path) -> Project:
    if run_git(root, "rev-parse", "--is-inside-work-tree") == "true":
        listed = run_git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
        files = [f for f in listed.split("\0") if f and not is_ignored(f) and (root / f).is_file()]
        return Project(root, True, tuple(sorted(set(files))))
    return Project(root, False, tuple(sorted(walk(root))))


def extension(rel: str) -> str:
    name = rel.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[-1].lower() if "." in name[1:] else ""


def is_source(rel: str) -> bool:
    return extension(rel) in LANGUAGES


def read_bytes(path: Path, limit: int = 1 << 20) -> bytes:
    try:
        with path.open("rb") as handle:
            return handle.read(limit)
    except OSError:
        return b""


def line_count(data: bytes) -> int:
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def read_text(path: Path) -> str:
    return read_bytes(path, 4 << 20).decode("utf-8", "ignore")


def scan_sources(project: Project, sources: list[str], resolver: Resolver) -> SourceScan:
    lines: dict[str, int] = {}
    markers: dict[str, list[str]] = {}
    per_file: dict[str, FileFacts] = {}
    rust_test_blocks = 0
    for rel in sources[:SCAN_CAP]:
        data = read_bytes(project.root / rel)
        lines[rel] = line_count(data)
        text = data.decode("utf-8", "ignore")
        for marker in FRAMEWORK_MARKERS + MAIN_MARKERS:
            if marker in text:
                markers.setdefault(marker, []).append(rel)
        if rel.endswith(".rs"):
            rust_test_blocks += text.count("#[cfg(test)]")
        per_file[rel] = analyze(rel, text, resolver, test=is_test_file(rel))
    return SourceScan(lines, markers, rust_test_blocks, len(sources) > SCAN_CAP, aggregate(per_file.values(), is_test_file), per_file)


def tier_for(source_count: int, line_count: int) -> str:
    if source_count < 5:
        return "empty"
    if source_count <= SMALL_FILES and line_count <= SMALL_LINES:
        return "small"
    return "large"


def origin_slug(root: Path) -> str:
    url = run_git(root, "config", "--get", "remote.origin.url")
    if not url:
        return ""
    slug = re.sub(r"^(?:git@|https?://|ssh://git@)", "", url).replace(":", "/", 1)
    return re.sub(r"\.git$", "", slug)


def drift_lines(root: Path, branch: str) -> tuple[str, ...]:
    lines = []
    counts = run_git(root, "rev-list", "--left-right", "--count", "HEAD...@{upstream}")
    if counts:
        ahead, behind = counts.split()
        lines.append(f"{ahead} ahead / {behind} behind upstream")
    default = run_git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if default and default != f"origin/{branch}":
        behind = run_git(root, "rev-list", "--count", f"HEAD..{default}")
        if behind and behind != "0":
            lines.append(f"{behind} behind {default}")
    return tuple(f"{line} (local refs, not fetched)" for line in lines)


def nested_worktrees(root: Path) -> tuple[str, ...]:
    resolved = root.resolve()
    nested = []
    for line in run_git(root, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = Path(line[len("worktree "):]).resolve()
            if path != resolved and resolved in path.parents:
                nested.append(path.relative_to(resolved).as_posix())
    for entry in run_git(root, "ls-files", "--others", "--directory", "--exclude-standard").splitlines():
        if entry.endswith("/") and entry.count("/") <= 2 and (root / entry / ".git").exists() and entry.rstrip("/") not in nested:
            nested.append(entry.rstrip("/"))
    return tuple(sorted(nested))


def directory_size(path: Path) -> str:
    try:
        output = subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True, timeout=10).stdout
        kilobytes = int(output.split()[0])
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return ""
    return f" ({kilobytes >> 10} MB)" if kilobytes >= 1024 else ""


def ignored_entries(root: Path) -> tuple[str, ...]:
    noise = re.compile(r"cache|^__pycache__/$|^\.DS_Store$|^node_modules/$|^target/$|^dist/$|^build/$|^\.git/$")
    listing = run_git(root, "ls-files", "--others", "--ignored", "--exclude-standard", "--directory")
    entries = []
    for entry in listing.splitlines():
        if entry.count("/") > (1 if entry.endswith("/") else 0) or noise.search(entry):
            continue
        path = root / entry
        if entry.endswith("/"):
            entries.append(entry + directory_size(path))
        else:
            size = path.stat().st_size if path.exists() else 0
            entries.append(f"{entry} ({size >> 20} MB)" if size >= 1 << 20 else entry)
    return tuple(entries)


def git_state(root: Path) -> GitState:
    branch = run_git(root, "branch", "--show-current") or "detached HEAD"
    commits = int(run_git(root, "rev-list", "--count", "HEAD") or 0)
    last = run_git(root, "log", "-1", "--format=%cs (%cr)") or "no commits"
    staged = modified = 0
    untracked = []
    for line in run_git(root, "status", "--porcelain", "--untracked-files=all", strip=False).splitlines():
        if len(line) < 4:
            continue
        code, path = line[:2], line[3:]
        if code == "??":
            untracked.append(path)
            continue
        staged += code[0] not in " ?!"
        modified += code[1] not in " ?!"
    return GitState(branch, commits, last, staged, modified, tuple(untracked), drift_lines(root, branch), nested_worktrees(root), ignored_entries(root))


def header_lines(project: Project, state: GitState | None) -> list[str]:
    lines = [f"PRIME SURVEY: {project.root.name}  ({project.root})"]
    if state is None:
        return lines + ["git: not a repository"]
    tree = f"{state.staged} staged, {state.modified} modified, {len(state.untracked)} untracked" if (state.staged or state.modified or state.untracked) else "clean"
    parts = [f"git: {state.branch}", f"{state.commits} commits", f"last {state.last}", tree]
    slug = origin_slug(project.root)
    if slug:
        parts.append(f"origin {slug}")
    lines.append(" | ".join(parts))
    if state.drift:
        lines.append("  upstream: " + "; ".join(state.drift))
    untracked_source = [p for p in state.untracked if is_source(p) or p.endswith((".md", ".toml", ".yaml", ".yml", ".json"))]
    if untracked_source:
        hidden = len(state.untracked) - len(untracked_source)
        label = f"  untracked source and docs ({len(untracked_source)}" + (f" of {len(state.untracked)}" if hidden else "") + "): "
        cap = 25 if len(untracked_source) <= 25 else 15
        lines.append(label + ", ".join(untracked_source[:cap]) + (f", +{len(untracked_source) - cap} more" if len(untracked_source) > cap else ""))
    if state.ignored:
        lines.append("  ignored at root: " + ", ".join(state.ignored[:12]) + (f", +{len(state.ignored) - 12} more" if len(state.ignored) > 12 else ""))
    if state.nested:
        lines.append("  nested worktrees (excluded here; exclude from greps too): " + ", ".join(state.nested[:8]))
    toplevel = run_git(project.root, "rev-parse", "--show-toplevel")
    if toplevel and Path(toplevel).resolve() != project.root.resolve():
        lines.append(f"  note: surveying a subdirectory of the repository at {toplevel}")
    return lines


def size_lines(sources: list[str], others: list[str], scan: SourceScan, state: GitState | None) -> list[str]:
    total_lines = sum(scan.lines.values())
    tier = tier_for(len(sources), total_lines)
    sampled = " (content scan sampled)" if scan.sampled else ""
    lines = [f"size: {len(sources)} source files, {total_lines:,} lines -> tier: {tier}{sampled}"]
    signals = []
    if state is not None and state.commits == 0:
        signals.append("no commits yet")
    if 0 < total_lines < 500:
        signals.append(f"only {total_lines} source lines")
    if signals:
        lines.append("scaffold signals: " + "; ".join(signals))
    by_language: Counter[str] = Counter()
    lines_by_language: Counter[str] = Counter()
    for rel in sources:
        language = LANGUAGES[extension(rel)]
        by_language[language] += 1
        lines_by_language[language] += scan.lines.get(rel, 0)
    languages = ", ".join(f"{lang} {n} ({lines_by_language[lang]:,} lines)" for lang, n in by_language.most_common(6))
    if languages:
        lines.append(f"languages: {languages}")
    other_kinds = Counter(extension(rel) or "(no ext)" for rel in others).most_common(6)
    if other_kinds:
        lines.append("other files: " + ", ".join(f"{kind} {n}" for kind, n in other_kinds))
    return lines


def layout_lines(files: Iterable[str], limits: Limits) -> list[str]:
    subtree: Counter[str] = Counter()
    children: dict[str, set[str]] = {}
    root_files = 0
    for rel in files:
        parts = rel.split("/")
        if len(parts) == 1:
            root_files += 1
            continue
        for depth in range(1, len(parts)):
            directory = "/".join(parts[:depth])
            subtree[directory] += 1
            children.setdefault("/".join(parts[:depth - 1]), set()).add(directory)
    top = sorted(children.get("", ()), key=lambda d: (-subtree[d], d))
    lines = ["layout:"]
    for directory in top[:limits.top_dirs]:
        lines.append(describe_directory(collapse_single_child(directory, children, subtree), subtree, children, limits))
    if len(top) > limits.top_dirs:
        lines.append(f"  +{len(top) - limits.top_dirs} more directories: " + ", ".join(top[limits.top_dirs:limits.top_dirs + 12]))
    lines.append(f"  root files: {root_files}")
    return lines


def collapse_single_child(directory: str, children: dict[str, set[str]], subtree: Counter[str]) -> str:
    while len(children.get(directory, ())) == 1:
        only = next(iter(children[directory]))
        if subtree[only] != subtree[directory]:
            break
        directory = only
    return directory


def describe_directory(directory: str, subtree: Counter[str], children: dict[str, set[str]], limits: Limits) -> str:
    kids = sorted(children.get(directory, ()), key=lambda k: (-subtree[k], k))
    direct = subtree[directory] - sum(subtree[k] for k in kids)
    label = f"  {directory}/ {subtree[directory]}"
    if kids and direct:
        label += f" ({direct} direct)"
    if not kids:
        return label
    largest = max(subtree[k] for k in kids)
    if len(kids) >= 8 and largest <= 3:
        return f"{label}: {len(kids)} subdirectories of {largest} file{'s' if largest > 1 else ''} or fewer"
    shown = ", ".join(f"{k.rsplit('/', 1)[-1]} {subtree[k]}" for k in kids[:limits.children])
    more = f", +{len(kids) - limits.children} more" if len(kids) > limits.children else ""
    return f"{label}: {shown}{more}"


def manifest_paths(files: Iterable[str]) -> list[str]:
    found = []
    for rel in files:
        if rel.count("/") > 3:
            continue
        name = rel.rsplit("/", 1)[-1]
        if name in MANIFEST_NAMES or rel in MANIFEST_NAMES or name.startswith(("Dockerfile", "requirements")) and (name == "Dockerfile" or name.endswith((".txt", ".in")) or name.startswith("Dockerfile.")):
            found.append(rel)
    return sorted(found, key=lambda p: (p.count("/"), p))


def load_toml(text: str) -> dict:
    if tomllib is None:
        return {}
    try:
        return tomllib.loads(text)
    except Exception:
        return {}


def requirement_name(spec: str) -> str:
    if " @ " in spec:
        return requirement_name(spec.split(" @ ")[0].strip())
    if spec.startswith(("git+", "http://", "https://")):
        return re.sub(r"\.git$", "", spec.rsplit("/", 1)[-1].split("@")[0].split("#")[0])
    return re.split(r"[\s<>=!~\[;]", spec, maxsplit=1)[0]


def requirements_names(text: str) -> list[str]:
    names = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            names.append(requirement_name(line))
    return names


def go_direct_deps(text: str) -> list[str]:
    names = []
    in_block = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("require ("):
            in_block = True
            continue
        if line == ")":
            in_block = False
            continue
        candidate = line[len("require "):] if line.startswith("require ") else (line if in_block else "")
        if not candidate or "// indirect" in candidate:
            continue
        module = candidate.split()[0]
        if "." in module.split("/")[0]:
            module = "/".join(module.split("/")[1:]) or module
        names.append(module)
    return names


def toml_section_keys(text: str, section: str) -> list[str]:
    match = re.search(rf"^\[{re.escape(section)}\]\s*$(.*?)(?=^\[|\Z)", text, re.M | re.S)
    if not match:
        return []
    return [m.group(1) for m in re.finditer(r"^([A-Za-z0-9_.-]+)\s*=", match.group(1), re.M)]


def script_command(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    if isinstance(value, dict):
        return str(value.get("cmd") or value.get("shell") or value.get("script") or value.get("call") or "")
    return ""


def parse_package_json(rel: str, text: str) -> Manifests:
    try:
        data = json.loads(text)
    except ValueError:
        return Manifests((rel,))
    scripts = data.get("scripts", {}) if isinstance(data.get("scripts"), dict) else {}
    entry = []
    for key in ("main", "module", "bin"):
        value = data.get(key)
        if isinstance(value, str):
            entry.append(f"{rel} {key}: {value}")
        elif isinstance(value, dict):
            entry.append(f"{rel} bin: " + ", ".join(f"{k} -> {v}" for k, v in list(value.items())[:4]))
    workspaces = data.get("workspaces")
    if isinstance(workspaces, dict):
        workspaces = workspaces.get("packages")
    workspace = ", ".join(workspaces) if isinstance(workspaces, list) else ""
    return Manifests(
        (rel,),
        tuple(data.get("dependencies", {}) or {}),
        tuple((data.get("devDependencies", {}) or {})),
        tuple((rel, name, str(cmd)) for name, cmd in scripts.items()),
        tuple(entry),
        workspace=workspace,
    )


def parse_pyproject(rel: str, text: str) -> Manifests:
    data = load_toml(text)
    project = data.get("project", {}) if data else {}
    poetry = data.get("tool", {}).get("poetry", {}) if data else {}
    runtime = [requirement_name(s) for s in project.get("dependencies", [])] if data else requirement_names(
        re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.M | re.S).group(1).replace('"', "\n").replace(",", "") if re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.M | re.S) else "")
    runtime += [k for k in poetry.get("dependencies", {}) if k != "python"]
    dev: list[str] = []
    for group in project.get("optional-dependencies", {}).values():
        dev += [requirement_name(s) for s in group]
    for group in (data.get("dependency-groups", {}) if data else {}).values():
        dev += [requirement_name(s) for s in group if isinstance(s, str)]
    for group in poetry.get("group", {}).values():
        dev += list(group.get("dependencies", {}))
    entry = [f"pyproject scripts: {name} = {target}" for name, target in {**project.get("scripts", {}), **poetry.get("scripts", {})}.items()]
    entry += [f"pyproject entry-points [{group}]: {len(items)}" for group, items in project.get("entry-points", {}).items()]
    commands = []
    tool = data.get("tool", {}) if data else {}
    for owner, key in (("poe", "tasks"), ("pdm", "scripts"), ("taskipy", "tasks")):
        for name, value in tool.get(owner, {}).get(key, {}).items():
            commands.append((f"{rel} [tool.{owner}]", name, script_command(value)))
    return Manifests((rel,), tuple(runtime), tuple(dev), tuple(commands), tuple(entry))


def parse_cargo(rel: str, text: str) -> Manifests:
    data = load_toml(text)
    runtime = list(data.get("dependencies", {})) + list(data.get("workspace", {}).get("dependencies", {})) if data else toml_section_keys(text, "dependencies")
    dev = list(data.get("dev-dependencies", {})) if data else toml_section_keys(text, "dev-dependencies")
    bins = data.get("bin", []) if data else []
    entry = [f"Cargo [[bin]] {b.get('name', '?')}: {b.get('path', 'src/main.rs')}" for b in bins if isinstance(b, dict)]
    members = data.get("workspace", {}).get("members", []) if data else []
    return Manifests((rel,), tuple(runtime), tuple(dev), (), tuple(entry), workspace=", ".join(members))


def parse_makefile(rel: str, text: str) -> Manifests:
    commands = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^([A-Za-z][A-Za-z0-9_./-]*)\s*:(?!=)", line)
        if not match or "%" in match.group(1):
            continue
        following = lines[index + 1] if index + 1 < len(lines) else ""
        commands.append((rel, match.group(1), following.strip().rstrip("\\").strip() if following.startswith("\t") else ""))
    return Manifests((rel,), commands=tuple(commands))


def parse_taskfile(rel: str, text: str) -> Manifests:
    names: list[str] = []
    descriptions: dict[str, str] = {}
    first_command: dict[str, str] = {}
    in_tasks = False
    current = None
    list_key = ""
    expect_block = False
    block: list[str] = []
    block_indent = None

    def flush() -> None:
        nonlocal block, block_indent
        if block and current:
            first_command.setdefault(current, " ; ".join(block[:2]) + (" ... (multi-line)" if len(block) > 2 else ""))
        block, block_indent = [], None

    for line in text.splitlines():
        if re.match(r"^tasks:\s*$", line):
            in_tasks = True
            continue
        if in_tasks and re.match(r"^\S", line):
            flush()
            in_tasks = False
        if not in_tasks:
            continue
        indent = len(line) - len(line.lstrip())
        if block_indent is not None:
            if line.strip() and indent >= block_indent:
                if len(block) < 3:
                    block.append(line.strip())
                continue
            flush()
        named = re.match(r"^  ([A-Za-z0-9_:.-]+):\s*$", line)
        if named:
            current = named.group(1)
            names.append(current)
            list_key = ""
            expect_block = False
            continue
        if current is None:
            continue
        if expect_block and line.strip():
            block_indent = indent
            block = [line.strip()]
            expect_block = False
            continue
        key = re.match(r"^    ([A-Za-z_]+):\s*(.*)$", line)
        if key:
            list_key, value = key.group(1), key.group(2).strip()
            if list_key == "cmd" and value in ("|", ">"):
                expect_block = True
            elif list_key == "cmd" and value:
                first_command.setdefault(current, unquote(value))
            elif list_key == "desc" and value:
                descriptions[current] = unquote(value)
            continue
        item = re.match(r"^\s+-\s+(?:cmd:\s*)?(.+)$", line)
        if item and list_key == "cmds" and current not in first_command:
            if item.group(1).strip() in ("|", ">"):
                expect_block = True
            else:
                first_command[current] = unquote(item.group(1))
    flush()
    commands = tuple((rel, name, first_command.get(name) or descriptions.get(name, "")) for name in names)
    return Manifests((rel,), commands=commands)


def parse_justfile(rel: str, text: str) -> Manifests:
    commands = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^(?:@)?([A-Za-z_][A-Za-z0-9_-]*)(?:\s+[^:=]*)?:\s*(.*)$", line)
        if not match or ":=" in line:
            continue
        following = lines[index + 1].strip() if index + 1 < len(lines) and lines[index + 1].startswith((" ", "\t")) else ""
        commands.append((rel, match.group(1), following or match.group(2)))
    return Manifests((rel,), commands=tuple(commands))


def parse_dockerfile(rel: str, text: str) -> Manifests:
    entry = [f"{rel} {m.group(1)}: {m.group(2).strip()}" for m in re.finditer(r"^(CMD|ENTRYPOINT)\s+(.+)$", text, re.M)]
    return Manifests((rel,), entrypoints=tuple(entry[-2:]))


def parse_compose(rel: str, text: str) -> Manifests:
    match = re.search(r"^services:\s*$(.*?)(?=^\S|\Z)", text, re.M | re.S)
    services = re.findall(r"^  ([A-Za-z0-9_.-]+):\s*$", match.group(1), re.M) if match else []
    return Manifests((rel,), compose_services=tuple(services))


def parse_procfile(rel: str, text: str) -> Manifests:
    return Manifests((rel,), entrypoints=tuple(f"Procfile {line.strip()}" for line in text.splitlines() if ":" in line))


def parse_manifest(project: Project, rel: str) -> Manifests:
    name = rel.rsplit("/", 1)[-1]
    text = read_text(project.root / rel)
    if name == "package.json":
        return parse_package_json(rel, text)
    if name == "pyproject.toml":
        return parse_pyproject(rel, text)
    if name == "Cargo.toml":
        return parse_cargo(rel, text)
    if name == "go.mod":
        return Manifests((rel,), tuple(go_direct_deps(text)))
    if name == "Gemfile":
        return Manifests((rel,), tuple(re.findall(r"^\s*gem\s+['\"]([^'\"]+)", text, re.M)))
    if name == "composer.json":
        try:
            data = json.loads(text)
            return Manifests((rel,), tuple(data.get("require", {})), tuple(data.get("require-dev", {})))
        except ValueError:
            return Manifests((rel,))
    if name.startswith("requirements") and name.endswith((".txt", ".in")):
        return Manifests((rel,), tuple(requirements_names(text)))
    if name == "Makefile":
        return parse_makefile(rel, text)
    if name in ("Taskfile.yml", "Taskfile.yaml"):
        return parse_taskfile(rel, text)
    if name in ("justfile", "Justfile"):
        return parse_justfile(rel, text)
    if name.startswith("Dockerfile"):
        return parse_dockerfile(rel, text)
    if name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        return parse_compose(rel, text)
    if name == "Procfile":
        return parse_procfile(rel, text)
    if name == "go.work":
        return Manifests((rel,), workspace=", ".join(re.findall(r"^\s*(?:use\s+)?(\./\S+)", text, re.M)))
    if name == "pnpm-workspace.yaml":
        return Manifests((rel,), workspace=", ".join(re.findall(r"^\s*-\s*['\"]?([^'\"\n]+)", text, re.M)))
    return Manifests((rel,))


def merge(parsed: Iterable[Manifests]) -> Manifests:
    items = list(parsed)
    return Manifests(
        tuple(p for m in items for p in m.paths),
        tuple(dict.fromkeys(d for m in items for d in m.runtime)),
        tuple(dict.fromkeys(d for m in items for d in m.dev)),
        tuple(c for m in items for c in m.commands),
        tuple(e for m in items for e in m.entrypoints),
        tuple(dict.fromkeys(s for m in items for s in m.compose_services)),
        "; ".join(m.workspace for m in items if m.workspace),
    )


def manifest_lines(project: Project, manifests: Manifests) -> list[str]:
    root_level = [p for p in manifests.paths if "/" not in p]
    nested = [p for p in manifests.paths if "/" in p]
    lines = []
    if root_level:
        lines.append("manifests: " + ", ".join(root_level))
    if nested:
        lines.append(f"nested manifests ({len(nested)}): " + ", ".join(nested[:14]) + (f", +{len(nested) - 14} more" if len(nested) > 14 else ""))
    managers = sorted({LOCKFILES[f.rsplit('/', 1)[-1]] for f in project.files if f.rsplit("/", 1)[-1] in LOCKFILES and f.count("/") < 2})
    if managers:
        lines.append("package manager: " + ", ".join(managers))
    if manifests.workspace:
        lines.append(f"workspace members: {manifests.workspace}")
    if manifests.compose_services:
        lines.append("compose services: " + ", ".join(manifests.compose_services))
    workflows = sorted(f.rsplit("/", 1)[-1] for f in project.files if f.startswith(".github/workflows/") and f.endswith((".yml", ".yaml")))
    if workflows:
        lines.append(f"workflows ({len(workflows)}): " + ", ".join(workflows[:10]) + (f", +{len(workflows) - 10} more" if len(workflows) > 10 else ""))
    terraform = sum(1 for f in project.files if f.endswith(".tf"))
    if terraform:
        lines.append(f"terraform files: {terraform}")
    return lines


def runner_for(source: str) -> str:
    name = source.rsplit("/", 1)[-1].split(" ")[0]
    if name.startswith("Makefile"):
        return "make"
    if name.startswith("Taskfile") or "[tool.taskipy]" in source:
        return "task"
    if name.lower() == "justfile":
        return "just"
    if name == "package.json":
        return "npm run"
    if "[tool.poe]" in source:
        return "poe"
    if "[tool.pdm]" in source:
        return "pdm run"
    return ""


def command_label(source: str, name: str) -> str:
    runner = runner_for(source)
    return f"{runner} {name}" if runner else name


def command_lines(manifests: Manifests, limits: Limits) -> list[str]:
    if not manifests.commands:
        return ["commands: none declared (no Makefile, Taskfile, justfile, or package.json scripts)"]

    def priority(command: tuple[str, str, str]) -> tuple[int, str]:
        name = command[1].lower()
        rank = next((i for i, key in enumerate(PRIORITY_COMMANDS) if key in name), len(PRIORITY_COMMANDS))
        return (rank, name)

    ordered = sorted(manifests.commands, key=priority)
    lines = [f"commands ({len(ordered)} declared, from " + ", ".join(dict.fromkeys(c[0] for c in ordered)) + "):"]
    for source, name, cmd in ordered[:limits.commands]:
        shown = (cmd[:limits.command_width - 3] + "...") if len(cmd) > limits.command_width else cmd
        label = command_label(source, name)
        lines.append(f"  {label}: {shown}" if shown else f"  {label}")
    if len(ordered) > limits.commands:
        lines.append(f"  +{len(ordered) - limits.commands} more: " + ", ".join(c[1] for c in ordered[limits.commands:limits.commands + 15]))
    return lines


def dependency_lines(manifests: Manifests, limits: Limits) -> list[str]:
    lines = []
    for label, names in (("runtime", manifests.runtime), ("dev", manifests.dev)):
        if not names:
            continue
        shown = ", ".join(names[:limits.dependencies])
        more = f", +{len(names) - limits.dependencies} more" if len(names) > limits.dependencies else ""
        lines.append(f"  {label} ({len(names)}): {shown}{more}")
    return ["dependencies:"] + lines if lines else []


def script_callers(project: Project, manifests: Manifests) -> dict[str, list[str]]:
    """Map each script's basename to the declared commands, container entrypoints, and CI steps that name it."""
    texts = [(command_label(source, name), cmd) for source, name, cmd in manifests.commands]
    texts += [(entry.split(" ")[0], entry) for entry in manifests.entrypoints]
    texts += [("ci", cmd) for _, cmd in ci_run_lines(project)]
    callers: dict[str, list[str]] = {}
    for rel in project.files:
        if not is_script_path(rel):
            continue
        basename = rel.rsplit("/", 1)[-1]
        if len(basename.rsplit(".", 1)[0]) < 4:
            continue
        labels = [label for label, text in texts if basename in text]
        if labels:
            callers[basename] = list(dict.fromkeys(labels))
    return callers


def script_lines(project: Project, manifests: Manifests, limits: Limits) -> list[str]:
    paths = [rel for rel in project.files if is_script_path(rel) and not is_test_file(rel)]
    if not paths:
        return []
    callers = script_callers(project, manifests)
    entries = []
    for rel in paths:
        data = read_bytes(project.root / rel, 4000)
        if b"\0" in data:
            continue
        used = callers.get(rel.rsplit("/", 1)[-1], [])
        entries.append((0 if used else 1, rel, doc_line(data.decode("utf-8", "ignore")), used))
    entries.sort()
    homes = Counter(rel.rsplit("/", 1)[0] + "/" if "/" in rel else "(root)" for _, rel, _, _ in entries)
    lines = [f"scripts ({len(entries)} in " + ", ".join(home for home, _ in homes.most_common(3)) + "):"]
    for _, rel, doc, used in entries[:limits.scripts]:
        line = f"  {rel}" + (f" — {doc}" if doc else "") + (f" (used by {', '.join(used[:3])})" if used else "")
        lines.append(line[:limits.command_width + 60])
    if len(entries) > limits.scripts:
        rest = [rel.rsplit("/", 1)[-1] for _, rel, _, _ in entries[limits.scripts:]]
        lines.append(f"  +{len(rest)} more: " + ", ".join(rest[:15]) + (", ..." if len(rest) > 15 else ""))
    return lines


def mostly(where: Counter, count: int, overall: Counter) -> str:
    if count < 3 or not where:
        return ""
    directory, hits = where.most_common(1)[0]
    if not directory or hits / count < 0.6:
        return ""
    if overall and overall[directory] / max(sum(overall.values()), 1) >= 0.6:
        return ""
    return f" (mostly {directory}/)"


def library_lines(facts: CodeFacts, manifests: Manifests, limits: Limits) -> list[str]:
    declared = {normalize(name): name for name in manifests.runtime + manifests.dev}
    lines = []
    if facts.external:
        shown = facts.external.most_common(limits.libraries)
        parts = [f"{declared.get(key, key)} {n}{mostly(facts.external_dirs.get(key, Counter()), n, facts.dirs)}" for key, n in shown]
        more = f", +{len(facts.external) - len(shown)} more" if len(facts.external) > len(shown) else ""
        lines.append(f"libraries in use ({facts.analyzed} non-test files; files importing each): " + ", ".join(parts) + more)
    if facts.external_test_only:
        lines.append("  test-only: " + ", ".join(f"{declared.get(key, key)} {n}" for key, n in facts.external_test_only.most_common(8)))
    if declared and facts.analyzed:
        unused = [name for name in manifests.runtime if normalize(name) not in facts.external and normalize(name) not in facts.external_test_only and not is_tool(name)]
        if unused:
            lines.append(f"  declared runtime, never imported: " + ", ".join(unused[:10]) + (f", +{len(unused) - 10} more" if len(unused) > 10 else ""))
        undeclared = [(key, n) for key, n in facts.external.most_common() if key not in declared]
        if undeclared:
            lines.append("  imported, not declared (transitive or local?): " + ", ".join(f"{key} {n}" for key, n in undeclared[:8]))
    return lines


def hub_lines(facts: CodeFacts, limits: Limits) -> list[str]:
    hubs = facts.hubs.most_common(limits.hubs)
    if not hubs:
        return []
    return ["internal hubs (files importing each): " + ", ".join(f"{path} {n}" for path, n in hubs)]


def stdlib_lines(facts: CodeFacts) -> list[str]:
    items = sorted(facts.stdlib.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:10]
    if not items:
        return []
    parts = []
    for module, paths in items:
        if len(paths) <= 5:
            parts.append(f"{module} {len(paths)} ({', '.join(paths)})")
        else:
            where = Counter("/".join(p.split("/")[:2]) if p.count("/") >= 2 else p.rsplit("/", 1)[0] if "/" in p else "" for p in paths)
            parts.append(f"{module} {len(paths)}{mostly(where, len(paths), facts.dirs)}")
    return ["stdlib signals (files): " + "; ".join(parts)]


def pattern_lines(facts: CodeFacts, limits: Limits) -> list[str]:
    def row(label: str, counter: Counter, kind: str, cap: int) -> str:
        items = counter.most_common(cap)
        if not items:
            return ""
        parts = []
        for name, n in items:
            paths = facts.files.get((kind, name), [])
            example = facts.examples.get((kind, name))
            where = ", ".join(paths) if n <= 3 and paths else (example.path if example else "")
            parts.append(f"{name} {n}" + (f" ({where})" if where else ""))
        return f"  {label}: " + ", ".join(parts) + (f", +{len(counter) - cap} more" if len(counter) > cap else "")

    rows = [
        row("decorators", facts.decorators, "decorator", limits.pattern_items),
        row("base classes", facts.bases, "base", limits.pattern_items),
        row("idioms", facts.idioms, "idiom", limits.pattern_items + 2),
        row("tests", facts.test_idioms, "test", 6),
    ]
    if facts.definition_files >= 3:
        rows.insert(3, f"  typed signatures: {round(100 * facts.typed_files / facts.definition_files)}% of files with definitions")
    rows = [r for r in rows if r]
    return ["patterns (files, non-test; in parentheses: every file when three or fewer, else the heaviest user):"] + rows if rows else []


def entrypoint_targets(manifests: Manifests, scan: SourceScan, sources: list[str], resolver: Resolver) -> list[str]:
    """Files worth outlining, best first: declared script targets, framework wiring, main guards, then by name."""
    ordered = []
    for entry in manifests.entrypoints:
        for module in re.findall(r"\b([A-Za-z_][\w.]*):[A-Za-z_]\w*\b", entry):
            if path := resolver.python_module_path(module):
                ordered.append(path)
        for token in re.findall(r"[\w./-]+\.(?:sh|py|js|ts|mjs|go|rs|rb)\b", entry):
            candidate = token.lstrip("./")
            if candidate in resolver.files:
                ordered.append(candidate)
    for marker in FRAMEWORK_MARKERS + MAIN_MARKERS:
        ordered += sorted((p for p in scan.markers.get(marker, []) if not is_test_file(p)), key=lambda p: (p.count("/"), p))
    ordered += sorted((rel for rel in sources if rel.rsplit("/", 1)[-1].rsplit(".", 1)[0] in ENTRY_STEMS and not is_test_file(rel)), key=lambda p: (p.count("/"), p))
    return list(dict.fromkeys(ordered))


def outline_lines(project: Project, targets: list[str], scan: SourceScan, limits: Limits) -> list[str]:
    lines = []
    for rel in targets:
        facts = scan.per_file.get(rel)
        text = read_text(project.root / rel)
        header = f"outline {rel} ({scan.lines.get(rel, line_count(text.encode()))} lines"
        if facts:
            internal = list(dict.fromkeys(facts.internal))[:8]
            external = list(dict.fromkeys(facts.external))[:8]
            if internal:
                header += "; imports " + ", ".join(internal)
            if external:
                header += "; uses " + ", ".join(external)
        lines.append(header + "):")
        lines += outline(rel, text, limits.outline_lines) or ["  (no top-level definitions found)"]
    return lines


def is_test_file(rel: str) -> bool:
    parts = rel.split("/")
    name = parts[-1]
    if any(p in ("tests", "test", "__tests__", "spec", "testing", "e2e", "cypress", "integration_tests") for p in parts[:-1]):
        return True
    if name.startswith("test_") or name.startswith("conftest"):
        return True
    if name.endswith(("_test.py", "_test.go", "_test.rs", "_spec.rb", "Test.java", "Tests.java", "Tests.swift", "Test.kt", "_test.dart", "_test.exs")):
        return True
    return re.search(r"\.(test|spec)\.[cm]?[jt]sx?$", name) is not None


def entrypoint_lines(project: Project, manifests: Manifests, scan: SourceScan, sources: list[str]) -> list[str]:
    lines = [f"  {entry}" for entry in manifests.entrypoints[:10]]
    listed: set[str] = set()
    for marker in MAIN_MARKERS + FRAMEWORK_MARKERS:
        paths = [p for p in scan.markers.get(marker, []) if not is_test_file(p)]
        if not paths:
            continue
        listed.update(paths)
        label = "__main__ guard" if marker.startswith("if __name__") else marker
        shown = ", ".join(sorted(paths, key=lambda p: (p.count("/"), p))[:5])
        more = f" (+{len(paths) - 5} more)" if len(paths) > 5 else ""
        lines.append(f"  {label}: {shown}{more}")
    by_name = [
        rel for rel in sources
        if rel.rsplit("/", 1)[-1].rsplit(".", 1)[0] in ENTRY_STEMS and rel not in listed and not is_test_file(rel)
    ]
    by_name.sort(key=lambda p: (p.count("/"), p))
    if by_name:
        lines.append("  by name: " + ", ".join(by_name[:10]) + (f" (+{len(by_name) - 10} more)" if len(by_name) > 10 else ""))
    return ["entrypoints:"] + lines if lines else ["entrypoints: none found"]


def ci_run_lines(project: Project) -> list[tuple[str, str]]:
    """Every single-line `run:` step in the GitHub workflows, as (workflow file, command)."""
    steps = []
    for rel in project.files:
        if not (rel.startswith(".github/workflows/") and rel.endswith((".yml", ".yaml"))):
            continue
        for line in read_text(project.root / rel).splitlines():
            match = re.match(r"^\s*(?:-\s*)?run:\s*(.+)$", line)
            if match and match.group(1).strip() not in ("|", ">"):
                steps.append((rel.rsplit("/", 1)[-1], match.group(1).strip()))
    return steps


def ci_test_commands(project: Project) -> list[str]:
    keywords = ("test", "pytest", "jest", "vitest", "mocha", "cargo", "go ", "lint", "ruff", "eslint", "mypy", "pyright", "tsc", "typecheck", "task ", "make ", "just ", "npm run", "pnpm ", "yarn ", "bun ")
    by_workflow: dict[str, list[str]] = {}
    for workflow, command in ci_run_lines(project):
        if any(k in command for k in keywords):
            by_workflow.setdefault(workflow, []).append(command[:60])
    findings = [f"  ci {workflow}: " + "; ".join(dict.fromkeys(commands))[:160] for workflow, commands in by_workflow.items()]
    return findings[:5]


def test_lines(project: Project, sources: list[str], scan: SourceScan) -> list[str]:
    tests = [rel for rel in sources if is_test_file(rel)]
    lines = []
    if tests:
        by_top: Counter[str] = Counter()
        for rel in tests:
            parts = rel.split("/")
            top = parts[0] if len(parts) > 1 else "(root)"
            colocated = top not in ("tests", "test", "__tests__", "spec", "e2e")
            by_top[f"{top}/ (co-located)" if colocated else f"{top}/"] += 1
        lines.append(f"tests: {len(tests)} files -> " + ", ".join(f"{k} {n}" for k, n in by_top.most_common(6)))
    else:
        lines.append("tests: no test files found")
    if scan.rust_test_blocks:
        lines.append(f"  rust #[cfg(test)] modules: {scan.rust_test_blocks}")
    config_names = ("pytest.ini", "tox.ini", "conftest.py", "jest.config.js", "jest.config.ts", "vitest.config.ts", "vitest.config.js", "playwright.config.ts", "cypress.config.ts", "cypress.config.js", ".mocharc.yml", ".mocharc.json", "jest-setup.ts", "setup.cfg", "noxfile.py")
    configs = Counter(f.rsplit("/", 1)[-1] for f in project.files if f.rsplit("/", 1)[-1] in config_names)
    if configs:
        lines.append("  config: " + ", ".join(f"{name} x{n}" if n > 1 else name for name, n in sorted(configs.items())))
    ci = ci_test_commands(project)
    if not any(f.startswith(".github/workflows/") for f in project.files):
        ci = ["  ci: no GitHub workflows"]
    return lines + ci


DOC_COMMAND = re.compile(r"`((?:uv run|uvx|poetry run|pipenv run|pytest|python -m pytest|npm (?:run|test)|pnpm (?:run|test)|yarn (?:run|test)?|bun (?:run|test)|make|task|just|cargo (?:test|build|run|clippy)|go (?:test|build|run|vet)|mix|bundle exec|rake|dotnet test|gradle|mvn|tox|nox|ruff|mypy|pyright|basedpyright|eslint|tsc)\b[^`]{0,90})`")


def doc_command_lines(project: Project) -> list[str]:
    found: dict[str, str] = {}
    for rel in project.files:
        if "/" in rel or not re.match(r"^(README|CLAUDE|AGENTS|CONTRIBUTING|DEVELOPMENT|HACKING)[^/]*\.md$", rel, re.I):
            continue
        for match in DOC_COMMAND.finditer(read_text(project.root / rel)):
            found.setdefault(match.group(1).strip(), rel)
    if not found:
        return []
    shown = [f"{cmd} ({rel})" for cmd, rel in list(found.items())[:6]]
    return ["commands in docs: " + "; ".join(shown) + (f"; +{len(found) - 6} more" if len(found) > 6 else "")]


def doc_lines(project: Project) -> list[str]:
    pattern = re.compile(r"^(README|CONTRIBUTING|ARCHITECTURE|DESIGN|CLAUDE|AGENTS|CHANGELOG|CONTEXT|GEMINI|COPILOT|HACKING|DEVELOPMENT|ONBOARDING)[^/]*\.(md|rst|txt)$", re.I)
    found = []
    for rel in project.files:
        if pattern.match(rel):
            found.append(f"{rel} ({line_count(read_bytes(project.root / rel))} lines)")
    for directory in ("docs", "doc", ".claude", "adr", "docs/adr", "docs/decisions", "doc/adr", "specs"):
        count = sum(1 for f in project.files if f.startswith(directory + "/"))
        if count:
            found.append(f"{directory}/ {count} files")
    return ["docs: " + ", ".join(found)] if found else ["docs: none"]


def activity_lines(project: Project) -> list[str]:
    if not project.is_git:
        return []
    log = run_git(project.root, "log", "--since=90.days", "--format=%x00%an", "--name-only", "--", ".")
    if not log:
        return ["activity (90d): no commits"]
    authors = set()
    touched: Counter[str] = Counter()
    commits = 0
    for line in log.splitlines():
        if line.startswith("\0"):
            commits += 1
            authors.add(line[1:])
        elif line.strip():
            touched["/".join(line.split("/")[:2]) if "/" in line else "(root)"] += 1
    present = set(project.files)
    hot = ", ".join(f"{d} {n}" + ("" if (project.root / d).is_dir() or d in present or d == "(root)" else " (gone)") for d, n in touched.most_common(6))
    return [f"activity (90d): {commits} commits by {len(authors)} authors; most touched: {hot}"]


GREP_EXCLUDES = (":!*.lock", ":!*lock.json", ":!*.sum", ":!CHANGELOG.md")


def reference_count(root: Path, names: Iterable[str]) -> int:
    patterns = [n for n in names if len(n) >= 4]
    if not patterns:
        return 0
    args = ["grep", "-l", "-i", "-F"]
    for pattern in patterns:
        args += ["-e", pattern]
    hits = run_git(root, *args, "--", ".", *GREP_EXCLUDES)
    return len(hits.splitlines()) if hits else 0


def project_names(project: Project) -> list[str]:
    name = project.root.name
    names = [name]
    prefix = project.root.parent.name + "-"
    if name.startswith(prefix) and len(name) - len(prefix) >= 4:
        names.append(name[len(prefix):])
    return names


def sibling_evidence(project: Project, repo: Path, manifests: Manifests, own_names: list[str]) -> tuple[tuple[int, int], list[str]]:
    dependency_names = {d.rsplit("/", 1)[-1].lower() for d in manifests.runtime + manifests.dev}
    evidence, rank = [], 9
    if repo.name.lower() in dependency_names:
        evidence.append("dependency")
        rank = 0
    if repo.name in manifests.compose_services:
        evidence.append("compose service")
        rank = min(rank, 1)
    reverse = reference_count(repo, own_names)
    if reverse:
        evidence.append(f"{reverse} there")
        rank = min(rank, 2)
    if repo.name.lower() in project.root.name.lower():
        evidence.append("name prefix")
    elif project.is_git:
        forward = reference_count(project.root, [repo.name])
        if forward:
            evidence.append(f"{forward} here")
            rank = min(rank, 3 if "-" in repo.name or "_" in repo.name else 4)
    return (rank, -reverse), evidence


def sibling_lines(project: Project, manifests: Manifests, limits: Limits) -> list[str]:
    parent = project.root.parent
    try:
        neighbors = sorted(d for d in parent.iterdir() if d.is_dir() and d.resolve() != project.root.resolve() and not d.name.startswith("."))
    except OSError:
        return []
    repos = [d for d in neighbors if (d / ".git").exists()]
    manifest_only = [d.name for d in neighbors if d not in repos and any((d / m).exists() for m in ("package.json", "pyproject.toml", "go.mod", "Cargo.toml"))]
    if not repos and not manifest_only:
        return ["siblings: none (no other git repositories or manifests next to this project)"]
    own_names = project_names(project) if len(repos) <= 80 else []
    own_org = origin_slug(project.root).rsplit("/", 1)[0]
    same_org = 0
    referenced, unreferenced = [], []
    for repo in repos:
        if own_org and origin_slug(repo).startswith(own_org + "/"):
            same_org += 1
        rank, evidence = sibling_evidence(project, repo, manifests, own_names)
        (referenced if evidence else unreferenced).append((rank, repo.name, evidence))
    referenced.sort(key=lambda item: (item[0], item[1]))
    org_note = f", {same_org} share origin org {own_org}" if own_org and same_org else ""
    lines = [f"siblings: {len(repos)} git repos in {parent}{org_note}" + ("" if own_names else " (too many for reference checks)")]
    if referenced:
        shown = referenced[:limits.siblings]
        lines.append('  related, strongest first ("64 there" = files there mentioning this project, "2 here" = files here naming it): ' + ", ".join(f"{name} ({', '.join(ev)})" for _, name, ev in shown) + (f", +{len(referenced) - limits.siblings} more" if len(referenced) > limits.siblings else ""))
    if unreferenced:
        names = [name for _, name, _ in unreferenced]
        lines.append("  no reference either way: " + ", ".join(names[:limits.siblings]) + (f", +{len(names) - limits.siblings} more" if len(names) > limits.siblings else ""))
    if manifest_only:
        lines.append("  non-git neighbors with manifests: " + ", ".join(manifest_only[:10]))
    return lines


def go_module_name(project: Project, manifests: Manifests) -> str:
    for rel in manifests.paths:
        if rel.rsplit("/", 1)[-1] == "go.mod":
            match = re.search(r"^module\s+(\S+)", read_text(project.root / rel), re.M)
            if match:
                return match.group(1)
    return ""


def survey(root: Path, limits: Limits) -> list[str]:
    project = discover(root)
    state = git_state(root) if project.is_git else None
    sources = [f for f in project.files if is_source(f)]
    others = [f for f in project.files if not is_source(f)]
    manifests = merge(parse_manifest(project, rel) for rel in manifest_paths(project.files))
    resolver = Resolver.build(project.files, manifests.runtime + manifests.dev, go_module_name(project, manifests))
    scan = scan_sources(project, sources, resolver)
    tier = tier_for(len(sources), sum(scan.lines.values()))
    sections = [header_lines(project, state), size_lines(sources, others, scan, state)]
    if tier == "empty":
        sections.append(manifest_lines(project, manifests) or ["manifests: none"])
        sections.append([f"files: {len(project.files)} total -> " + ", ".join(project.files[:12]) + (" ..." if len(project.files) > 12 else "")])
        return [line for section in sections for line in section]
    targets = entrypoint_targets(manifests, scan, sources, resolver)[:limits.outlines]
    hubs = [path for path, _ in scan.facts.hubs.most_common() if path in resolver.files and path not in targets][:limits.hub_outlines]
    sections += [
        layout_lines(project.files, limits),
        manifest_lines(project, manifests),
        command_lines(manifests, limits),
        doc_command_lines(project),
        script_lines(project, manifests, limits),
        dependency_lines(manifests, limits),
        library_lines(scan.facts, manifests, limits),
        hub_lines(scan.facts, limits),
        stdlib_lines(scan.facts),
        pattern_lines(scan.facts, limits),
        entrypoint_lines(project, manifests, scan, sources),
        outline_lines(project, targets + hubs, scan, limits),
        test_lines(project, sources, scan),
        doc_lines(project),
        activity_lines(project),
        sibling_lines(project, manifests, limits),
    ]
    return [line for section in sections if section for line in section]


def main(argv: list[str]) -> int:
    if any(arg in ("-h", "--help") for arg in argv):
        print("usage: survey.py [--full] [project-path]   (defaults to the current directory; --full lifts the list caps)")
        return 0
    limits = Limits.unlimited() if "--full" in argv else Limits()
    positional = [arg for arg in argv if not arg.startswith("--")]
    root = Path(positional[0] if positional else ".").expanduser().resolve()
    if not root.is_dir():
        print(f"survey.py: not a directory: {root}", file=sys.stderr)
        return 2
    print("\n".join(survey(root, limits)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
