# killall-skills

Skills and agents for Claude Code, Codex, and Cursor (beta).

## Install

Claude Code:

```
/plugin marketplace add killallgit/killall-skills
/plugin install killall-skills@killallgit
```

Codex:

```
codex plugin marketplace add killallgit/killall-skills
codex plugin add killall-skills@killallgit
```

Cursor: in **Customize**, install from the repository URL
`https://github.com/killallgit/killall-skills`. Cursor reads
`.cursor-plugin/plugin.json`.

Any host, skills only, through the skills CLI:

```
npx skills add killallgit/killall-skills
```

Claude Code runs a skill as `/name`; Codex runs it as `$name`.

### What each host gets

| Host | Skills | Agents in `agents/` |
| --- | --- | --- |
| Claude Code | All | All, from the plugin |
| Codex | All | None. Codex plugins do not carry agents |
| Cursor | All | None yet. The agents use Claude Code frontmatter |
| Skills CLI | All | None |

## Factory builder

`/factory-builder` installs rails for running a repository's work as parallel
sub-agents, each lane in its own worktree and verified before it lands. It
defers to the structure tool the repo already uses (gstack, mattpocock/skills,
agent-skills, Spec Kit) for specs, plans, and reviews, and makes sure that
tool's skills are installed and visible to Claude, Codex, and Cursor. Without
one, it asks, or installs the factory's own spec, review, and approve loop.
`/factory-builder uninstall` (or `remove`) takes out everything it added.
User-invoked only.

## Git janitor

In Claude Code, `/git-janitor` cleans the current repository. Pass a path to
target another repository, or add `audit-only` to inspect without removing
anything. The plugin-qualified command is `/killall-skills:git-janitor`.

For a separate conversation context, ask Claude Code to use the
`killall-skills:git-janitor` agent and include the repository path and any
scope limits. The agent uses the same skill and returns a cleanup receipt.
Its context is separate; it operates on the repository's actual worktrees.

## Prime

In Claude Code, `/prime` maps the current project before work starts as a
terse list of facts: layout, entrypoints and flow, core patterns, load-bearing
libraries, useful scripts and commands, and related repositories. A bundled
survey script does the discovery in one read-only command — imports counted by
file, internal hubs, pattern and test-idiom counts, outlines of the
entrypoints, scripts with their doc lines — so the pass needs at most three
capped reads, no subagents, and adds well under fifty thousand tokens. It ends
at the map, and it switches to the `caveman` skill first when that is
installed, so the map and everything said around it stay terse. User-invoked
only, so it never fires on its own and costs nothing but its one-line
description until you run it.
