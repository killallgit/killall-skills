# killall-skills

Domain-focused workflow skills for Claude Code and Codex.

## What ships

- `plugins/planning/` — project planning, PRDs, issue slicing, triage, and wayfinding.
- `plugins/engineering/` — implementation, diagnosis, review, proof recordings, Git maintenance, and delivery.
- `plugins/architecture/` — domain modeling and deep-module design.
- `plugins/knowledge/` — research, handoffs, and cross-project wikis.
- `plugins/experimental/` — prototypes and extension authoring.
- `rules/` and root `hooks/` — installable repo rules and optional host hooks.

## Install

```bash
git clone https://github.com/killallgit/killall-skills
cd killall-skills
./install.sh --list
./install.sh planning engineering
```

The installer refreshes only the selected domain plugins in every supported
host found on `PATH`. Select all five explicitly with `./install.sh --all`, or
remove selected domains with `./install.sh --remove knowledge`. Restart Claude
Code and Codex after either operation.

Install one skill without its whole domain through the cross-agent skills CLI:

```bash
npx skills@latest add killallgit/killall-skills \
  --skill research \
  --agent claude-code \
  --agent codex \
  --global \
  --yes
```

<details>
<summary>Manual install</summary>

```bash
# Claude Code
claude plugin marketplace add killallgit/killall-skills
claude plugin install planning@killallgit

# Codex
codex plugin marketplace add killallgit/killall-skills
codex plugin add planning@killallgit
```

</details>

## Local development

```bash
claude --plugin-dir ~/Code/killallgit/killall-skills/plugins/planning
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

Releases are intentionally manual. Update the version in every domain's Claude
and Codex manifests and add the release notes to `CHANGELOG.md`, then commit,
tag, and publish:

```bash
git commit -am "chore: release X.Y.Z"
git tag "killall-skills--vX.Y.Z"
git push origin main "killall-skills--vX.Y.Z"
gh release create "killall-skills--vX.Y.Z" \
  --title "killall-skills X.Y.Z" \
  --notes-file /path/to/release-notes.md
```
