# killall-skills

Workflow skills for Claude Code and Codex.

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

`killall-skills` installs every skill. To install one, use its name instead,
for example `git-janitor@killallgit`. Pick either the bundle or individual
skills, not both.

Any host, skills only, through the skills CLI:

```
npx skills add killallgit/killall-skills
```

Claude Code runs a skill as `/name`; Codex runs it as `$name`.

## Ship

`/ship` opens a PR, waits for CodeRabbit, fixes its findings, merges, syncs
main, and runs the git janitor. If CodeRabbit is rate-limited it stops and
asks you.

Installing it also installs a `PreToolUse` hook that blocks `gh pr merge` until
the merged PR's CodeRabbit check has succeeded. The hook only applies in repos
with a `.coderabbit.yaml`, and only runs on Claude Code. Codex installs the
plugin but the hook is not supported or tested there.

## Development

`.claude-plugin/marketplace.json` is generated from each skill's `SKILL.md`
frontmatter and `marketplace.config.json`; Claude Code and Codex both read it.
After adding, renaming, or editing a skill description:

```
task manifests
```

CI fails when the committed file is out of date.

A skill can ship hooks in `skills/<name>/hooks/hooks.json`; the generator inlines
them into that skill's entry and into the `killall-skills` bundle.

To release, run one of these from anywhere in the checkout. The release runs in
a temporary worktree off `origin/main`, so your checkout is never switched. It
runs the tests and `generate_manifests.py --check` first, and on a failed push
it removes the tag it created:

```
task tag:patch
task tag:minor
task tag:major
```

It rebases main on origin, bumps `version` in `marketplace.config.json`,
regenerates the manifest, commits, tags `vX.Y.Z`, and pushes main and the tag.
It refuses to run with a dirty working tree.

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
