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

## Agents

Agent definitions and project setup live in [killall-agents](https://github.com/killallgit/killall-agents).

## Git janitor

In Claude Code, `/git-janitor` cleans the current repository. Pass a path to
target another repository, or add `audit-only` to inspect without removing
anything. The plugin-qualified command is `/killall-skills:git-janitor`.

For a separate conversation context, mention `@agent-killall-agents:git-janitor`
in Claude Code with the repository path and any scope limits. This requires
the separate agents plugin. The agent uses the same skill and returns a cleanup receipt.
Its context is separate; it operates on the repository's actual worktrees.

## Independent review

`/independent-review` gets the current branch reviewed by something that did
not write it. It opens a PR if the branch has none, then waits for CodeRabbit
and resolves its comments. When CodeRabbit is not installed, rate limited, or
skipped, it dispatches a local review agent with fresh context (never the
current session) and resolves that agent's findings instead. It reports what
was fixed and declined, and leaves the PR open. User-invoked only.

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
