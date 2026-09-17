#!/usr/bin/env python3
"""Build an isolated Git repository for git-janitor evaluations."""

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


def commit(repo: Path, name: str, date: str = "2026-09-10T12:00:00Z") -> str:
    (repo / name).write_text(name + "\n")
    git(repo, "add", name, date=date)
    git(repo, "commit", "-m", name, date=date)
    return git(repo, "rev-parse", "HEAD")


def main() -> None:
    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=False)
    repo = root / "repo"
    subprocess.run(["git", "init", "-q", "-b", "trunk", str(repo)], check=True)
    git(repo, "config", "user.name", "Fixture")
    git(repo, "config", "user.email", "fixture@example.test")
    base = commit(repo, "base.txt", date="2024-12-01T12:00:00Z")
    git(repo, "branch", "main")

    git(repo, "switch", "-q", "-c", "merged/cleanup")
    commit(repo, "merged.txt")
    git(repo, "switch", "-q", "trunk")
    git(repo, "merge", "-q", "--no-ff", "merged/cleanup", "-m", "merge cleanup")
    git(repo, "worktree", "add", "-q", str(root / "clean-tree"), "merged/cleanup")

    git(repo, "switch", "-q", "-c", "feature/post-merge")
    commit(repo, "first-feature.txt", date="2026-09-14T12:00:00Z")
    git(repo, "switch", "-q", "trunk")
    git(repo, "merge", "--squash", "feature/post-merge", date="2026-09-15T12:00:00Z")
    git(repo, "commit", "-m", "squash first feature", date="2026-09-15T12:00:00Z")
    git(repo, "switch", "-q", "feature/post-merge")
    current_pr_head = commit(repo, "later-local-work.txt", date="2026-09-16T12:00:00Z")
    git(repo, "switch", "-q", "trunk")

    git(repo, "switch", "-q", "-c", "feature/active")
    active_head = commit(repo, "active-feature.txt", date="2026-09-16T12:00:00Z")
    git(repo, "switch", "-q", "trunk")

    git(repo, "switch", "-q", "-c", "spike/stale", base)
    commit(repo, "stale-experiment.txt", date="2025-01-01T12:00:00Z")
    git(repo, "switch", "-q", "trunk")

    git(repo, "switch", "-q", "-c", "feature/dirty")
    commit(repo, "dirty-feature.txt", date="2026-09-16T12:00:00Z")
    git(repo, "switch", "-q", "trunk")
    git(repo, "worktree", "add", "-q", str(root / "dirty-tree"), "feature/dirty")
    (root / "dirty-tree" / "untracked-notes.txt").write_text("keep this work\n")

    prs = {
        "feature/post-merge": [
            {"number": 12, "state": "MERGED", "mergedAt": "2026-09-15T12:00:00Z",
             "headRefOid": current_pr_head, "baseRefName": "trunk", "url": "https://example.test/pr/12"}
        ],
        "feature/active": [
            {"number": 13, "state": "OPEN", "mergedAt": None,
             "headRefOid": active_head, "baseRefName": "trunk", "url": "https://example.test/pr/13"}
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
        "    if head == 'spike/stale': sys.exit(1)\n"
        "    data = json.loads((Path(__file__).parent.parent / 'prs.json').read_text()).get(head, [])\n"
        "    state = args[args.index('--state') + 1] if '--state' in args else 'open'\n"
        "    print(json.dumps(data if state == 'all' else [p for p in data if p['state'].lower() == state]))\n"
        "else:\n"
        "    sys.exit(2)\n"
    )
    shim.chmod(0o755)
    print(json.dumps({"repo": str(repo), "gh_shim": str(bin_dir), "clean_tree": str(root / "clean-tree"),
                      "dirty_tree": str(root / "dirty-tree")}))


if __name__ == "__main__":
    main()
