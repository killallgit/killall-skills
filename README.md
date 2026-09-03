# killall-skills

Domain-focused workflow skills for coding agents.

## What ships

- `skills/planning/` — project planning, PRDs, issue slicing, triage, and wayfinding.
- `skills/engineering/` — implementation, diagnosis, review, Git maintenance, and delivery.
- `skills/architecture/` — domain modeling and deep-module design.
- `skills/knowledge/` — research, handoffs, and cross-project wikis.
- `skills/experimental/` — prototypes and extension authoring.
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
  --skill research \
  --skill diagnose \
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
npx skills@latest remove research
```

## Agents

The `skills` CLI installs skills, not subagents. Three skills call subagents that
live in `agents/`: `git-janitor` uses `git-janitor-investigator`, `project-planner`
has a matching agent, and `commenator` audits comments on demand. Copy the ones
you want into your agent directory:

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
