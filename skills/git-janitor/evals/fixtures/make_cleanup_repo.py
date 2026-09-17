#!/usr/bin/env python3
"""Build a disposable repository with dirty and unpublished worktrees."""

import json
import os
import subprocess
import sys
from pathlib import Path


def git(repo: Path, *args: str, date: str = "2026-09-10T12:00:00Z") -> str:
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = date
    env["GIT_COMMITTER_DATE"] = date
    return subprocess.check_output(["git", "-C", str(repo), *args], env=env, text=True).strip()


def commit(repo: Path, name: str, content: str, date: str) -> str:
    (repo / name).write_text(content)
    git(repo, "add", name, date=date)
    git(repo, "commit", "-m", name, date=date)
    return git(repo, "rev-parse", "HEAD")


def main() -> None:
    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=False)
    repo = root / "repo"
    remote = root / "remote.git"
    subprocess.run(["git", "init", "-q", "-b", "trunk", str(repo)], check=True)
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    git(repo, "config", "user.name", "Fixture")
    git(repo, "config", "user.email", "fixture@example.test")
    base = commit(repo, "config.txt", "old\n", "2024-12-01T12:00:00Z")
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-q", "-u", "origin", "trunk")

    git(repo, "switch", "-q", "-c", "merged/cleanup")
    commit(repo, "merged.txt", "landed\n", "2026-09-01T12:00:00Z")
    git(repo, "switch", "-q", "trunk")
    git(repo, "merge", "-q", "--no-ff", "merged/cleanup", "-m", "merge cleanup")
    git(repo, "worktree", "add", "-q", str(root / "merged-tree"), "merged/cleanup")

    git(repo, "branch", "superseded/work")
    (repo / "config.txt").write_text("current\n")
    (repo / "ready.txt").write_text("ready\n")
    git(repo, "add", "config.txt", "ready.txt")
    git(repo, "commit", "-m", "replace old config", date="2026-09-10T12:00:00Z")
    git(repo, "worktree", "add", "-q", str(root / "superseded-tree"), "superseded/work")
    (root / "superseded-tree" / "config.txt").write_text("current\n")
    (root / "superseded-tree" / "ready.txt").write_text("ready\n")

    git(repo, "switch", "-q", "-c", "old/spike", base)
    commit(repo, "old-spike.txt", "abandoned experiment\n", "2025-01-01T12:00:00Z")
    git(repo, "switch", "-q", "trunk")
    git(repo, "worktree", "add", "-q", str(root / "old-tree"), "old/spike")

    git(repo, "switch", "-q", "-c", "old/recent-dirty", base)
    commit(repo, "old-dirty.txt", "historical work\n", "2025-01-02T12:00:00Z")
    git(repo, "switch", "-q", "trunk")
    git(repo, "worktree", "add", "-q", str(root / "recent-dirty-tree"), "old/recent-dirty")
    (root / "recent-dirty-tree" / "new-idea.txt").write_text("new customer idea, still relevant\n")

    git(repo, "switch", "-q", "-c", "active/unpushed")
    git(repo, "push", "-q", "-u", "origin", "HEAD:refs/heads/active/unpushed")
    active_tip = commit(repo, "active.txt", "unfinished active work\n", "2026-09-16T12:00:00Z")
    git(repo, "switch", "-q", "trunk")
    git(repo, "worktree", "add", "-q", str(root / "active-tree"), "active/unpushed")

    git(repo, "switch", "-q", "-c", "old/unpushed", base)
    git(repo, "push", "-q", "-u", "origin", "HEAD:refs/heads/old/unpushed")
    old_tip = commit(repo, "old-unpushed.txt", "old unpublished work\n", "2025-01-03T12:00:00Z")
    git(repo, "switch", "-q", "trunk")
    git(repo, "worktree", "add", "-q", str(root / "old-unpushed-tree"), "old/unpushed")

    prs = {
        "active/unpushed": [
            {"number": 43, "state": "OPEN", "mergedAt": None, "updatedAt": "2026-09-16T12:00:00Z",
             "headRefOid": active_tip, "baseRefName": "trunk", "url": "https://example.test/pr/43"}
        ],
        "old/unpushed": [
            {"number": 42, "state": "OPEN", "mergedAt": None, "updatedAt": "2025-01-03T12:00:00Z",
             "headRefOid": old_tip, "baseRefName": "trunk", "url": "https://example.test/pr/42"}
        ],
    }
    (root / "prs.json").write_text(json.dumps(prs))
    bin_dir = root / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "gh"
    shim.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "from pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "if args[:2] == ['repo', 'view']:\n"
        "    print(json.dumps({'defaultBranchRef': {'name': 'trunk'}}))\n"
        "elif args[:2] == ['pr', 'list']:\n"
        "    head = args[args.index('--head') + 1] if '--head' in args else ''\n"
        "    data = json.loads((Path(__file__).parent.parent / 'prs.json').read_text()).get(head, [])\n"
        "    state = args[args.index('--state') + 1] if '--state' in args else 'open'\n"
        "    print(json.dumps(data if state == 'all' else [p for p in data if p['state'].lower() == state]))\n"
        "else:\n"
        "    sys.exit(2)\n"
    )
    shim.chmod(0o755)
    print(json.dumps({"repo": str(repo), "gh_shim": str(bin_dir)}))


if __name__ == "__main__":
    main()
