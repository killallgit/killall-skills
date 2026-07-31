# killall-skills

Engineering workflow skills — project scoping, planning
(brief -> PRD -> issues -> TDD), cross-project knowledge wikis, triage,
diagnostics, and tooling — for Claude Code and Codex.

## What ships

- `payload/skills/` — installable skills, including project-planner, the
  PRD/issues/TDD workflow, and generic cross-project wiki setup and maintenance.
- `payload/agents/` — Claude Code subagents, including project-planner and
  git-janitor helpers.
- `rules/` and root `hooks/` — installable repo rules and optional host hooks.

## Install

```bash
git clone https://github.com/killallgit/killall-skills
cd killall-skills
./install.sh
```

The installer idempotently installs or refreshes the plugin in every supported
host found on `PATH`. Re-run it after `git pull`, or use `./install.sh --remove`
to uninstall it. Restart Claude Code and Codex after either operation.

<details>
<summary>Manual install</summary>

```bash
# Claude Code
claude plugin marketplace add killallgit/killall-skills
claude plugin install killall-skills@killallgit

# Codex
codex plugin marketplace add killallgit/killall-skills
codex plugin add killall-skills@killallgit
```

</details>

## Local development

```bash
claude --plugin-dir ~/Code/killallgit/killall-skills
```

## Proofcast

Proofcast records one agent command or focused validation flow as an H.264 MP4.
It requires Bash, [asciinema](https://asciinema.org/),
[AGG](https://github.com/asciinema/agg), FFmpeg with `libx264`, and
[Task](https://taskfile.dev/).

```bash
task install
proofcast --out smoke-test.mp4 -- python3 smoke_test.py
```

Without `--out`, Proofcast writes a timestamped MP4 in the current directory.
It prints the recorded command output and then the absolute video path. A failed
command is still rendered and Proofcast returns that command's exit status.

Recording is explicitly activated by saying “let's record this.” Proofcast
captures output verbatim and performs no automatic secret redaction, so never
record commands that print or contain credentials.

## Release

Releases are intentionally manual. Update the version in both plugin manifests
and add the release notes to `CHANGELOG.md`, then commit, tag, and publish:

```bash
git commit -am "chore: release X.Y.Z"
git tag "killall-skills--vX.Y.Z"
git push origin main "killall-skills--vX.Y.Z"
gh release create "killall-skills--vX.Y.Z" \
  --title "killall-skills X.Y.Z" \
  --notes-file /path/to/release-notes.md
```
