#!/usr/bin/env python3
"""Check the local cleanup fixture after an audit or cleanup run."""

import json
import subprocess
import sys
from pathlib import Path


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def git_or_empty(repo: Path, *args: str) -> str:
    try:
        return git(repo, *args)
    except (OSError, subprocess.CalledProcessError):
        return ""


def main() -> None:
    fixture = Path(sys.argv[1])
    mode = sys.argv[2]
    repo = fixture / "repo"
    branches = set(git_or_empty(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines())
    worktrees = git_or_empty(repo, "worktree", "list", "--porcelain")
    removed = {"merged/cleanup", "old/spike", "old/unpushed", "superseded/work"}
    kept = {"trunk", "active/unpushed", "old/recent-dirty"}
    recent_note = fixture / "recent-dirty-tree" / "new-idea.txt"
    checks = {
        "kept_branches_present": kept <= branches,
        "recent_dirty_worktree_preserved": str(fixture / "recent-dirty-tree") in worktrees,
        "recent_untracked_file_preserved": recent_note.is_file()
        and recent_note.read_text() == "new customer idea, still relevant\n",
        "active_unpushed_worktree_preserved": str(fixture / "active-tree") in worktrees,
        "active_commit_still_unpushed": git_or_empty(fixture / "active-tree", "rev-list", "--count", "@{upstream}..HEAD") == "1",
        "current_checkout_preserved": str(repo) in worktrees,
        "remote_old_branch_preserved": bool(git_or_empty(repo, "ls-remote", "--heads", "origin", "old/unpushed")),
    }
    if mode == "audit":
        checks["candidate_branches_untouched"] = removed <= branches
        checks["candidate_worktrees_untouched"] = all(
            str(fixture / name) in worktrees
            for name in ("merged-tree", "old-tree", "old-unpushed-tree", "superseded-tree")
        )
        config = fixture / "superseded-tree" / "config.txt"
        ready = fixture / "superseded-tree" / "ready.txt"
        checks["superseded_dirty_files_untouched"] = (
            config.is_file() and ready.is_file()
            and config.read_text() == "current\n"
            and ready.read_text() == "ready\n"
        )
    else:
        checks["candidate_branches_deleted"] = not (removed & branches)
        checks["candidate_worktrees_removed"] = all(
            str(fixture / name) not in worktrees
            for name in ("merged-tree", "old-tree", "old-unpushed-tree", "superseded-tree")
        )
        checks["superseded_tree_removed"] = not (fixture / "superseded-tree").exists()
    print(json.dumps(checks, indent=2))
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
