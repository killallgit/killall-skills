# killall-skills

Workflow skills for Claude Code, Codex, and Cursor (beta).

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

## Agent migration

Version **4.0.0** moves the agent catalog and `agent-setup` into
[killall-agents](https://github.com/killallgit/killall-agents). This repository
continues to provide all seven ordinary workflow skills, including `git-janitor`
and the original `follow-the-rules`. The agents package includes its own complete
copy of `follow-the-rules`.

For existing 3.x users:

1. Update `killall-skills` to 4.x through your host’s plugin manager.
2. Install the separate agents package, following its
   [installation instructions](https://github.com/killallgit/killall-agents#install).
3. Keep both plugins enabled if you use the git-janitor agent: it calls the
   `killall-skills:git-janitor` skill.

Update the skills plugin before enabling the agents plugin to avoid duplicate
agent/setup definitions. Claude’s agent prefix is now `killall-agents:`, while
ordinary skill commands keep the `killall-skills:` prefix. Run
`/killall-agents:agent-setup` in Claude Code or `$agent-setup` in Codex to refresh
project agents.

Existing generated agents remain in their projects and keep working. Their file
paths, ownership markers and work records at
`~/.config/killall-skills/agents/state/<encoded-main-checkout>/` are unchanged;
refresh/removal preserves lane JSON. See the
[setup guide](https://github.com/killallgit/killall-agents#project-setup).

The remaining git-janitor skill also works without the agents plugin; it inspects
branches inline when the optional investigator is unavailable.

## Git janitor

In Claude Code, `/git-janitor` cleans the current repository. Pass a path to
target another repository, or add `audit-only` to inspect without removing
anything. The plugin-qualified command is `/killall-skills:git-janitor`.

For a separate conversation context, ask Claude Code to use the
`killall-agents:git-janitor` agent from the separate agents plugin and include
the repository path and any scope limits. The agent uses the same skill and returns a cleanup receipt.
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
