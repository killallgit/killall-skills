# killall-skills

Domain-focused workflow skills for coding agents, packaged for the Codex
marketplace and the cross-agent `skills` CLI.

## What ships

- `GLOBAL_AGENT.md` — reusable baseline programming rules for global agent
  configuration.
- `.agents/plugins/marketplace.json` — the `killallgit` Codex marketplace.
- `plugins/planning/` — pre-spec project scoping.
- `plugins/engineering/` — library-usage review, Git maintenance, and waiting
  on CI.
- `plugins/knowledge/` — session catch-up, cross-project wikis, and upstream
  skill pointers.
- `plugins/experimental/` — extension authoring.
- `agents/` — optional Claude Code subagents used by some skills.
- `hooks/voice-readback/` — an optional turn-completion hook, registered only
  on request.

Each domain plugin contains a portable Agent Plugins `plugin.json`, a Codex
compatibility manifest at `.codex-plugin/plugin.json`, and its skills under
`skills/`.

## Install domain plugins in Codex

Add the marketplace once:

```bash
codex plugin marketplace add killallgit/killall-skills
```

Then install any domain:

```bash
codex plugin add planning@killallgit
codex plugin add engineering@killallgit
codex plugin add knowledge@killallgit
codex plugin add experimental@killallgit
```

Inspect or refresh the marketplace with:

```bash
codex plugin marketplace list
codex plugin marketplace upgrade killallgit
codex plugin list
```

For local development, add a checkout instead of the GitHub repository:

```bash
codex plugin marketplace add .
```

Restart the ChatGPT desktop app after adding or refreshing a local marketplace.

## Install individual skills

The cross-agent [`skills`](https://github.com/vercel-labs/skills) CLI discovers
the skills inside the domain plugins:

```bash
npx skills@latest add killallgit/killall-skills --list
```

Install only what you want, for the agents you use:

```bash
npx skills@latest add killallgit/killall-skills \
  --skill git-janitor \
  --skill wiki \
  --agent claude-code \
  --agent codex \
  --global \
  --yes
```

Install every skill with `--skill '*'`:

```bash
npx skills@latest add killallgit/killall-skills --skill '*' --agent codex -g -y
```

Skills land in each agent's own directory, including `~/.claude/skills/` for
Claude Code and `~/.codex/skills/` for Codex. Drop `--global` to install into
the current project.

Update or remove individual skills with:

```bash
npx skills@latest update
npx skills@latest remove git-janitor
```

## Skills that live upstream

The plan → implement → review → architect workflow lives in
[mattpocock/skills](https://github.com/mattpocock/skills). Install that catalog
for `setup-matt-pocock-skills`, `to-spec`, `to-tickets`, `triage`, `wayfinder`,
`tdd`, `code-review`, `diagnose`, `resolve-conflict`, `build-prototype`,
`research`, `handoff`, `codebase-design`, `domain-modeling`, and
`improve-codebase-architecture`.

```bash
npx skills@latest add mattpocock/skills
```

The `matt-pocock` skill maps previous workflow names to the upstream catalog
and explains the project files that its setup workflow expects.

## Optional Claude Code agents

Codex plugins in this repository contain skills only. Two Claude Code subagents
live in `agents/`: `git-janitor-investigator` supports `git-janitor`, and
`commenator` audits comments on demand. Copy them separately when wanted:

```bash
cp agents/*.md ~/.claude/agents/
```

Each skill still works without its agent by running the investigation inline.

## Local development

List skills from a checkout:

```bash
npx skills@latest add . --list
```

Run the tests with:

```bash
uv run --with pytest pytest tests -q
```
