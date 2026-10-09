#!/usr/bin/env python3
"""Project factory-builder templates into a repository.

Agent templates live in templates/. Each rendered agent is written once under
.factory/agents/<host>/ and symlinked into the directory that host reads.
The structure var picks the install set: "factory" installs the factory's own
spec, review, and approve loop; any other owner installs only the agents marked
"install: always" and the rails /factory skill.
.factory/ is gitignored local state. .worktreeinclude lists it so a new
worktree can receive the directory. Existing files are left alone unless
--force is set.

Everything the install adds is recorded in .factory/manifest.json so
uninstall_factory.py can take it out again.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
FACTORY_TEMPLATE = TEMPLATES / "factory.tmpl.md"
RAILS_TEMPLATE = TEMPLATES / "factory-rails.tmpl.md"
OWN_LOOP = "factory"
INSTALL = {"always", "loop"}
MANIFEST = Path(".factory/manifest.json")
SKILL_PATHS = (
    Path(".agents/skills/factory/SKILL.md"),
    Path(".claude/skills/factory/SKILL.md"),
    Path(".cursor/skills/factory/SKILL.md"),
)
RECORD: dict[str, list] = {"files": [], "links": [], "lines": []}
DASHBOARD = ROOT / "assets" / "dashboard.html"
HOSTS = {
    "claude": Path(".claude/agents"),
    "cursor": Path(".cursor/agents"),
    "codex": Path(".codex/agents"),
}

REQUIRED = (
    "project",
    "structure",
    "default_branch",
    "conventions",
    "gate",
    "spec_tool",
    "implement_tool",
    "review_tool",
    "isolation_note",
)
LENSES = ("code", "security", "ux", "design")
TOKEN = re.compile(r"\{\{([a-z_]+)\}\}")
SANDBOX = {"read-only", "workspace-write"}


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        raise SystemExit("template is missing frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise SystemExit("template frontmatter does not close")
    raw = text[4:end]
    body = text[end + 5 :].strip() + "\n"
    meta: dict[str, object] = {}
    lines = raw.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if ":" not in line:
            raise SystemExit(f"bad frontmatter line: {line}")
        key, value = line.split(":", 1)
        value = value.strip()
        index += 1
        if value in {"|", "|-"}:
            block: list[str] = []
            while index < len(lines) and (
                lines[index].startswith(" ") or lines[index].startswith("\t") or not lines[index].strip()
            ):
                block.append(lines[index][1:] if lines[index].startswith(" ") else lines[index])
                index += 1
            meta[key.strip()] = "\n".join(block).strip()
            continue
        if value in {"true", "false"}:
            meta[key.strip()] = value == "true"
        else:
            meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, body


def substitute(text: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise SystemExit(f"missing value for {{{{{key}}}}}")
        return values[key]

    rendered = TOKEN.sub(replace, text)
    leftover = TOKEN.findall(rendered)
    if leftover:
        raise SystemExit(f"unreplaced tokens: {', '.join(leftover)}")
    return rendered


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def toml_literal(value: str) -> str:
    if "'''" in value:
        raise SystemExit("a value contains ''' and cannot be written as a TOML literal")
    return "'''\n" + value.strip() + "\n'''"


def write(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        if path.read_text(encoding="utf-8") == content:
            RECORD["files"].append(path)
        print(f"skip {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    RECORD["files"].append(path)
    print(f"wrote {path}")


def claude_agent(meta: dict[str, object], body: str) -> str:
    tools = meta.get("claude_tools")
    if not isinstance(tools, str) or not tools:
        raise SystemExit(f"{meta.get('name')} is missing claude_tools")
    return (
        "---\n"
        f"name: {meta['name']}\n"
        f"description: {yaml_string(str(meta['description']))}\n"
        f"tools: {yaml_string(tools)}\n"
        "---\n\n"
        f"{body}"
    )


def cursor_agent(meta: dict[str, object], body: str) -> str:
    readonly = meta.get("cursor_readonly")
    if not isinstance(readonly, bool):
        raise SystemExit(f"{meta.get('name')} is missing cursor_readonly")
    flag = "true" if readonly else "false"
    return (
        "---\n"
        f"name: {meta['name']}\n"
        f"description: {yaml_string(str(meta['description']))}\n"
        "model: inherit\n"
        f"readonly: {flag}\n"
        "---\n\n"
        f"{body}"
    )


def codex_agent(meta: dict[str, object], body: str) -> str:
    sandbox = meta.get("codex_sandbox")
    if sandbox not in SANDBOX:
        raise SystemExit(f"{meta.get('name')} has codex_sandbox {sandbox!r}; expected read-only or workspace-write")
    return (
        f"name = {json.dumps(str(meta['name']))}\n"
        f"description = {toml_literal(str(meta['description']))}\n"
        f"sandbox_mode = {json.dumps(sandbox)}\n"
        f"developer_instructions = {toml_literal(body)}\n"
    )


def link_agent(canonical: Path, host_path: Path, force: bool) -> None:
    relative = Path(os.path.relpath(canonical, host_path.parent))
    if host_path.is_symlink() and host_path.readlink() == relative:
        RECORD["links"].append(host_path)
        print(f"skip {host_path}")
        return
    if host_path.exists() or host_path.is_symlink():
        if not force:
            print(f"skip {host_path}")
            return
        host_path.unlink()
    host_path.parent.mkdir(parents=True, exist_ok=True)
    host_path.symlink_to(relative)
    RECORD["links"].append(host_path)
    print(f"linked {host_path} -> {relative}")


def render_agent(template: Path, values: dict[str, str], dest: Path, force: bool) -> None:
    rendered = substitute(template.read_text(encoding="utf-8"), values)
    meta, body = parse_frontmatter(rendered)
    name = str(meta["name"])
    files = {
        "claude": (f"{name}.md", claude_agent(meta, body)),
        "cursor": (f"{name}.md", cursor_agent(meta, body)),
        "codex": (f"{name}.toml", codex_agent(meta, body)),
    }
    for host, (filename, content) in files.items():
        canonical = dest / ".factory" / "agents" / host / filename
        write(canonical, content, force)
        link_agent(canonical, dest / HOSTS[host] / filename, force)


def factory_skill(values: dict[str, str]) -> str:
    template = FACTORY_TEMPLATE if values["structure"] == OWN_LOOP else RAILS_TEMPLATE
    text = substitute(template.read_text(encoding="utf-8"), values)
    if not text.startswith("---\n"):
        raise SystemExit("factory template is missing frontmatter")
    return text if text.endswith("\n") else text + "\n"


def ensure_line(path: Path, line: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if line in {item.strip() for item in existing.splitlines()}:
        print(f"skip {path}")
        return
    RECORD["lines"].append({"file": path, "line": line, "created": not path.exists()})
    if existing and not existing.endswith("\n"):
        existing += "\n"
    path.write_text(existing + line + "\n", encoding="utf-8")
    print(f"wrote {path}")


def seed_factory(dest: Path, own_loop: bool, force: bool) -> None:
    ensure_line(dest / ".gitignore", ".factory/")
    ensure_line(dest / ".worktreeinclude", ".factory/")
    factory = dest / ".factory"
    write(factory / "board.json", '{"jobs": []}\n', force)
    if own_loop:
        write(
            factory / "backlog.md",
            "# Backlog\n\n"
            "Unchecked items are the queue for `/factory next`. "
            "Add a feature as `- [ ] short description`.\n",
            force,
        )
    write(factory / "dashboard.html", DASHBOARD.read_text(encoding="utf-8"), force)


def load_vars(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        raise SystemExit(f"vars missing {', '.join(missing)}")
    setup = data.get("setup", [])
    if not isinstance(setup, list) or any(
        not isinstance(item, dict) or set(item) != {"change", "revert"} for item in setup
    ):
        raise SystemExit("setup must be an array of {change, revert} objects")
    values = {key: str(data[key]) for key in REQUIRED}
    if values["structure"] != OWN_LOOP:
        values["lenses"] = ""
        values["lenses_agents"] = ""
        return values
    if "lenses" not in data:
        raise SystemExit("vars missing lenses, which the factory's own loop needs")
    lenses = data["lenses"]
    if not isinstance(lenses, list) or not lenses:
        raise SystemExit("lenses must be a non-empty array")
    unknown = [lens for lens in lenses if lens not in LENSES]
    if unknown:
        raise SystemExit(f"unknown lenses: {', '.join(unknown)}")
    values["lenses"] = ", ".join(lenses)
    values["lenses_agents"] = ", ".join(f"`review-{lens}`" for lens in lenses)
    return values


def save_manifest(dest: Path, structure: str, setup: list[dict[str, str]]) -> None:
    path = dest / MANIFEST
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def rel(item: Path) -> str:
        return item.relative_to(dest).as_posix()

    files = set(old.get("files", [])) | {rel(item) for item in RECORD["files"]}
    links = set(old.get("links", [])) | {rel(item) for item in RECORD["links"]}
    lines = old.get("lines", [])
    for item in RECORD["lines"]:
        entry = {"file": rel(item["file"]), "line": item["line"], "created": item["created"]}
        if not any(e["file"] == entry["file"] and e["line"] == entry["line"] for e in lines):
            lines.append(entry)
    changes = old.get("setup", [])
    changes += [item for item in setup if item not in changes]
    manifest = {
        "structure": structure,
        "files": sorted(files - {MANIFEST.as_posix()}),
        "links": sorted(links),
        "lines": lines,
        "setup": changes,
    }
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install factory files into a repository.")
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--vars", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    dest = args.dest.resolve()
    if not dest.is_dir():
        raise SystemExit(f"dest is not a directory: {dest}")
    if not (dest / ".git").exists():
        raise SystemExit(f"dest is not a git checkout: {dest}")

    values = load_vars(args.vars)
    setup = json.loads(args.vars.read_text(encoding="utf-8")).get("setup", [])
    own_loop = values["structure"] == OWN_LOOP
    for template in sorted(TEMPLATES.glob("*.tmpl.md")):
        if template in (FACTORY_TEMPLATE, RAILS_TEMPLATE):
            continue
        text = template.read_text(encoding="utf-8")
        install = parse_frontmatter(text)[0].get("install")
        if install not in INSTALL:
            raise SystemExit(f"{template.name} has install {install!r}; expected always or loop")
        if install == "loop" and not own_loop:
            continue
        if "{{lens}}" in text:
            for lens in values["lenses"].split(", "):
                render_agent(template, {**values, "lens": lens}, dest, args.force)
        else:
            render_agent(template, values, dest, args.force)

    skill = factory_skill(values)
    for relative in SKILL_PATHS:
        write(dest / relative, skill, args.force)
    seed_factory(dest, own_loop, args.force)
    save_manifest(dest, values["structure"], setup)


if __name__ == "__main__":
    main()
