"""Compare lane-agent metadata rendered by this checkout with agent-setup at an earlier git ref."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

EVALS = Path(__file__).resolve().parent
sys.path.insert(0, str(EVALS / "fixtures"))
sys.path.insert(0, str(EVALS))

from make_repo import LEGACY_VARS, build
from run import metadata, render, snapshot

AGENTS = ("builder", "reviewer", "hall-monitor")
PATHS = {
    "claude": ".claude/agents/{}.md",
    "cursor": ".cursor/agents/{}.md",
    "codex": ".codex/agents/{}.toml",
}
FIELDS = {
    "claude": ("name", "model", "effort", "tools", "skills"),
    "cursor": ("name", "model", "readonly"),
    "codex": ("name", "model", "model_reasoning_effort", "sandbox_mode"),
}


def agent_fields(tree: dict[str, str]) -> dict[str, object]:
    fields = {}
    for host, pattern in PATHS.items():
        for agent in AGENTS:
            path = pattern.format(agent)
            found = metadata(path, tree[path]) if path in tree else {}
            fields.update({f"{host}/{agent}.{key}": found.get(key) for key in FIELDS[host]})
    return fields


def main() -> None:
    ref = sys.argv[1]
    with tempfile.TemporaryDirectory() as tmp:
        old = snapshot(build(Path(tmp) / "old", {}, {"ref": ref}))
        current = build(Path(tmp) / "new", {})
        render(current, ["--vars", "{vars}"], LEGACY_VARS)
        new = snapshot(current)
    old_fields, new_fields = agent_fields(old), agent_fields(new)
    differences = [f"{key}: {old_fields[key]} -> {new_fields[key]}" for key in old_fields if old_fields[key] != new_fields[key]]
    print("\n".join(differences) or f"agent metadata matches {ref}")
    for label, paths in (("only in old", set(old) - set(new)), ("only in new", set(new) - set(old))):
        for path in sorted(paths):
            print(f"{label}: {path}")
    sys.exit(1 if differences else 0)


if __name__ == "__main__":
    main()
