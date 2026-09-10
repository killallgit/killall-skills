#!/usr/bin/env python3

import argparse
import copy
import json
import shlex
from datetime import datetime, timezone
from pathlib import Path


EVENT_SCRIPTS = {
    "SessionStart": "wiki-session-start.py",
    "SessionEnd": "wiki-session-end.py",
}


def _vault_marker(vault):
    return str(Path(vault).expanduser().resolve() / "hooks" / "wiki-session-")


def _command(vault, script_name):
    script = Path(vault).expanduser().resolve() / "hooks" / script_name
    return f"python3 {shlex.quote(str(script))}"


def _is_vault_handler(handler, vault):
    return _vault_marker(vault) in handler.get("command", "")


def merge_hooks(config, host, vault, remove=False):
    if host not in {"claude", "codex"}:
        raise ValueError(f"unsupported host: {host}")
    merged = copy.deepcopy(config)
    hooks = merged.setdefault("hooks", {})
    for event, script_name in EVENT_SCRIPTS.items():
        groups = []
        for group in hooks.get(event, []):
            retained = [
                handler
                for handler in group.get("hooks", [])
                if not _is_vault_handler(handler, vault)
            ]
            if retained:
                updated = copy.deepcopy(group)
                updated["hooks"] = retained
                groups.append(updated)
        if not remove:
            groups.append(
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": _command(vault, script_name),
                            "timeout": 5,
                        }
                    ]
                }
            )
        if groups:
            hooks[event] = groups
        else:
            hooks.pop(event, None)
    if not hooks:
        merged.pop("hooks", None)
    return merged


def _read_config(path):
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"invalid JSON object in {path}")
    return value


def _write_config(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = path.with_name(f"{path.name}.bak.{stamp}")
        backup.write_bytes(path.read_bytes())
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def update_config(path, host, vault, remove=False):
    path = Path(path).expanduser()
    existing = _read_config(path)
    merged = merge_hooks(existing, host, vault, remove=remove)
    if merged == existing:
        return False
    _write_config(path, merged)
    return True


def default_config(host):
    if host == "claude":
        return Path.home() / ".claude" / "settings.json"
    if host == "codex":
        return Path.home() / ".codex" / "hooks.json"
    raise ValueError(f"unsupported host: {host}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Merge or remove cross-project wiki lifecycle hooks."
    )
    parser.add_argument("--host", choices=("claude", "codex"), required=True)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--remove", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    config = args.config or default_config(args.host)
    changed = update_config(
        config,
        args.host,
        args.vault,
        remove=args.remove,
    )
    action = "removed" if args.remove else "installed"
    state = action if changed else "unchanged"
    print(f"{args.host} hooks: {state} ({config})")


if __name__ == "__main__":
    main()
