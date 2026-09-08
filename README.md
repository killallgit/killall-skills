# killall-skills

Domain-focused workflow skills for coding agents.

## What ships

- `skills/planning/` — pre-spec project scoping.
- `skills/engineering/` — library-usage review, Git maintenance, and waiting on CI.
- `skills/knowledge/` — session catch-up, cross-project wikis, and upstream skill pointers.
- `skills/experimental/` — extension authoring.
- `agents/` — Claude Code subagents used by some skills.
- `hooks/voice-readback/` — optional turn-completion hook, registered only on request.

## Install

Everything installs through the cross-agent [`skills`](https://github.com/vercel-labs/skills)
CLI, which reads the `skills/<domain>/<name>/` catalog directly.

```bash
npx skills@latest add killallgit/killall-skills --list
```

Install what you want, for the agents you use:

```bash
npx skills@latest add killallgit/killall-skills \
  --skill git-janitor \
  --skill wiki \
  --agent claude-code \
  --agent codex \
  --global \
  --yes
```

Take a whole domain by naming its skills, or take everything with `--skill '*'`:

```bash
npx skills@latest add killallgit/killall-skills --skill '*' --agent claude-code -g -y
```

Skills land in each agent's own directory — `~/.claude/skills/` for Claude Code,
`~/.codex/skills/` for Codex — so they work without any marketplace or plugin
host. Drop `--global` to install into the current project instead.

Update or remove them the same way:

```bash
npx skills@latest update
npx skills@latest remove git-janitor
```

## Skills that moved upstream

The plan → implement → review → architect workflow lives in
[mattpocock/skills](https://github.com/mattpocock/skills), which this repo used
to fork. Fifteen forks were removed: `setup-planning`, `to-prd`, `to-issues`,
`triage`, `wayfinder`, `tdd`, `code-review`, `diagnose`,
`resolving-merge-conflicts`, `prototype`, `research`, `handoff`,
`codebase-design`, `domain-modeling`, and `improve-codebase-architecture`.

Install the upstream set instead:

```bash
claude plugins install mattpocock-skills   # or: npx skills@latest add mattpocock/skills
```

The `matt-pocock` skill holds the old-name → upstream-name map and what changes
in a repo that the removed `setup-planning` had already configured.

## Agents

The `skills` CLI installs skills, not subagents. Two live in `agents/`:
`git-janitor` uses `git-janitor-investigator`, and `commenator` audits comments
on demand. Copy the ones you want into your agent directory:

```bash
cp agents/*.md ~/.claude/agents/
```

Each skill still works without its agent — it just runs the investigation inline.

## Local development

Point the CLI at a checkout instead of the GitHub repo:

```bash
npx skills@latest add ~/Code/killallgit/killall-skills --list
```

Run the tests with:

```bash
uv run --with pytest pytest tests -q
```
