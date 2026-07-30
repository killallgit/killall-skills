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
