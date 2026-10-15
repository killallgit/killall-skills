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
each lane against the spec and the `follow-the-rules` skill. It delegates small
changes too. Builders create worktrees and run commands; reviewers independently
run checks and return diff evidence for the orchestrator to judge.

| Host | How a session starts as the orchestrator |
| --- | --- |
| Claude Code | `"agent": "orchestrator"` in `.claude/settings.json`; `claude --agent` overrides it |
| Codex | A managed block with model, effort, and `developer_instructions` in `.codex/config.toml`; the project must be trusted |
| Cursor | An always-applied rule, `.cursor/rules/orchestrator.mdc` |

One shared template per role contains its instructions and host settings;
[the renderer](skills/agent-setup/scripts/render_agents.py) adapts them to Claude Markdown, Codex TOML, and Cursor
Markdown/rules. Current defaults:

| Role | Claude model / effort | Codex model / effort |
| --- | --- | --- |
| Orchestrator | Opus / high | `gpt-6-astra` / high |
| Builder | Sonnet / high | `gpt-6.1-sol` / high |
| Reviewer | Opus / high | `gpt-6.1-sol` / high |
| Hall-monitor | Sonnet / medium | `gpt-6-luna` / high |

Claude's orchestrator tool allowlist permits reading, searching, and delegation
to these three agents, with no shell, edit, or skill tool. Codex and Cursor use
delegation-only instructions; they do not enforce a separate write boundary for
the orchestrator. Codex subagents inherit the main session's permissions. Cursor
keeps its session model. See the [Claude](https://code.claude.com/docs/en/sub-agents)
and [Codex](https://learn.chatgpt.com/docs/agent-configuration/subagents) agent docs.

After updating the installed skill, rerun `/agent-setup` in an existing repository
to refresh its generated agents. Local edits to generated files are replaced;
edit the source templates to change defaults. Unrelated settings remain intact.
Conflicting files or root Codex model, effort, or instruction settings that setup
did not write require explicit approval before using `--force`.

Generated paths are locally ignored through `.git/info/exclude`; already-tracked
files stay tracked. It edits no instruction file.

Work state lives in `~/.config/killall-skills/agents/state/<encoded-main-checkout>/`
(or under `XDG_CONFIG_HOME`). The key replaces non-alphanumeric path characters
with `-`, in Claude's style. All hosts and linked worktrees share the main
checkout's folder. Setup writes a [short README and JSON example](skills/agent-setup/templates/state.md);
each builder owns one lane JSON and updates it at handoffs. The orchestrator
reads these records and sends verdicts back to the builder to persist.

The folder stays; a finished lane's record is removed after authorized integration
and cleanup of its clean worktree. Setup reruns and `/agent-setup remove` preserve
lane state. Removal clears generated definitions and local exclude entries,
including legacy output. Codex sessions need write access to the state folder,
for example with `codex --add-dir <state-folder>`. User-invoked only.
See the [factory-pattern research](docs/research/agent-factory-patterns.md) for sources and possible next steps.

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
