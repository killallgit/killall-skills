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

`/agent-setup` (`$agent-setup` in Codex) gives a repository an orchestrator and
three lane agents for Claude Code, Codex, and Cursor, filled with its own gate,
conventions, and worktree rules. Every session in the repository starts as the
orchestrator: it cuts a spec into lanes, starts a `builder` per lane in its own
git worktree, then has an independent `reviewer` and a `hall-monitor` check
each lane against the spec and the `follow-the-rules` skill. A small change with
no independent parts, it makes itself.

| Host | How a session starts as the orchestrator |
| --- | --- |
| Claude Code | `"agent": "orchestrator"` in `.claude/settings.json`; `claude --agent` overrides it |
| Codex | A `developer_instructions` block in `.codex/config.toml`; the project must be trusted |
| Cursor | An always-applied rule, `.cursor/rules/orchestrator.mdc` |

It writes only those files and the agent definitions, and edits no instruction
file. `/agent-setup remove` takes it all out again, including what earlier
versions wrote. User-invoked only.

## Git janitor

In Claude Code, `/git-janitor` cleans the current repository. Pass a path to
target another repository, or add `audit-only` to inspect without removing
anything. The plugin-qualified command is `/killall-skills:git-janitor`.

For a separate conversation context, ask Claude Code to use the
`killall-skills:git-janitor` agent and include the repository path and any
scope limits. The agent uses the same skill and returns a cleanup receipt.
Its context is separate; it operates on the repository's actual worktrees.

## End session

`/end-session` closes out a session. It fetches, fast-forwards local branches,
and rebases the session branch onto the default branch. Work that already
landed or was superseded is discarded with its worktree. Otherwise it asks
once whether a PR is required, opens one if so, and archives the session.
User-invoked only.

## Session eject

`/session-eject` saves the session's work before usage runs out. It tells
running subagents to wrap up and waits for their reports, then commits and
pushes every changed worktree. An open PR gets a comment on what landed and
what is left; a branch without one gets a draft PR titled
`[ejected session]: <short desc>`. `/session-eject now` skips the wait and
commits, pushes, and opens the draft PR at once. Work on the default branch
moves to an `eject/` branch first. It ends by printing a handoff paragraph to
paste into a fresh agent so it can resume. User-invoked only.
