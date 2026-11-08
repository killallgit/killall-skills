#!/usr/bin/env python3
"""Rank a repo's hotspots (churn x size) and change-coupled file pairs from git history.

Usage: hotspots.py [--repo PATH] [--since "6 months ago"] [--top 15]
"""
from __future__ import annotations

import argparse
import subprocess
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path, PurePath

NOISE = ("*.lock", "*-lock.json", "*.lockb", "go.sum", "*.min.*", "*.map", "*.snap", "CHANGELOG*")


@dataclass(frozen=True)
class Commit:
    sha: str
    files: frozenset[str]


@dataclass(frozen=True)
class Hotspot:
    path: str
    revisions: int
    lines: int

    @property
    def score(self) -> int:
        return self.revisions * self.lines


@dataclass(frozen=True)
class Coupling:
    left: str
    right: str
    shared: int
    degree: int


def parse_log(log: str) -> tuple[Commit, ...]:
    commits = []
    for chunk in filter(None, log.split("\x00")):
        sha, *files = chunk.strip().splitlines()
        commits.append(Commit(sha, frozenset(f for f in files if f and not is_noise(f))))
    return tuple(commits)


def is_noise(path: str) -> bool:
    return any(PurePath(path).match(pattern) for pattern in NOISE)


def churn(commits: tuple[Commit, ...]) -> dict[str, int]:
    return dict(Counter(f for commit in commits for f in commit.files))


def rank_hotspots(revisions: dict[str, int], sizes: dict[str, int]) -> tuple[Hotspot, ...]:
    spots = (Hotspot(path, revs, sizes[path]) for path, revs in revisions.items() if path in sizes)
    return tuple(sorted(spots, key=lambda h: -h.score))


def change_coupling(commits: tuple[Commit, ...], min_shared: int = 3, max_files: int = 30) -> tuple[Coupling, ...]:
    focused = tuple(c for c in commits if len(c.files) <= max_files)
    revisions = churn(focused)
    shared = Counter(pair for c in focused for pair in combinations(sorted(c.files), 2))
    pairs = (
        Coupling(left, right, n, round(100 * n / ((revisions[left] + revisions[right]) / 2)))
        for (left, right), n in shared.items()
        if n >= min_shared
    )
    return tuple(sorted(pairs, key=lambda p: (-p.degree, -p.shared)))


def git_log(repo: Path, since: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "log", "--no-merges", f"--since={since}", "--name-only", "--format=%x00%H"],
        check=True, capture_output=True, text=True,
    ).stdout


def line_counts(repo: Path, paths: set[str]) -> dict[str, int]:
    files = ((path, repo / path) for path in paths)
    return {path: file.read_bytes().count(b"\n") for path, file in files if file.is_file()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--since", default="6 months ago")
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args()

    commits = parse_log(git_log(args.repo, args.since))
    revisions = churn(commits)
    sizes = line_counts(args.repo, set(revisions))
    hotspots = rank_hotspots(revisions, sizes)
    coupled = tuple(p for p in change_coupling(commits) if p.left in sizes and p.right in sizes)

    print(f"## Hotspots ({len(commits)} commits since {args.since})\nrevs  lines  path")
    for spot in hotspots[: args.top]:
        print(f"{spot.revisions:>4}  {spot.lines:>5}  {spot.path}")
    print("\n## Change coupling\ndegree  shared  pair")
    for pair in coupled[: args.top]:
        print(f"{pair.degree:>5}%  {pair.shared:>6}  {pair.left} <-> {pair.right}")


if __name__ == "__main__":
    main()
