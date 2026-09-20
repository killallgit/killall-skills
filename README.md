# killall-skills

Claude Code plugin. Install it with:

```
/plugin marketplace add killallgit/killall-skills
/plugin install killall-skills@killallgit
```

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
