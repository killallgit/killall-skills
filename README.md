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

## Agent setup

`/agent-setup` (`$agent-setup` in Codex) gives a repository an `orchestrate`
skill and three agents for Claude Code, Codex, and Cursor, filled with its own
gate, conventions, and worktree rules. The main session runs `orchestrate`,
which cuts a spec into lanes and starts a `builder` per lane, working in
parallel in its own git worktree, then for every lane an independent `reviewer`
plus a `hall-monitor` that checks the `follow-the-rules` skill is followed. A
short block in each instruction file the hosts read tells whatever development
framework is in use, such as gstack, mattpocock/skills, or Spec Kit, to hand
parallel work to `orchestrate`. It installs nothing else.
`/agent-setup remove` takes it out again. User-invoked only.

## Git janitor

In Claude Code, `/git-janitor` cleans the current repository. Pass a path to
target another repository, or add `audit-only` to inspect without removing
anything. The plugin-qualified command is `/killall-skills:git-janitor`.

For a separate conversation context, ask Claude Code to use the
`killall-skills:git-janitor` agent and include the repository path and any
scope limits. The agent uses the same skill and returns a cleanup receipt.
Its context is separate; it operates on the repository's actual worktrees.
