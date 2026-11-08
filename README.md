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
The bundle is listed last so the skills CLI groups all skills under
`Killall Skills` instead of repeating each skill name as a group heading.

To release, run one of these from anywhere in the checkout. The release runs in
a temporary worktree off `origin/main`, so your checkout is never switched. It
runs the tests and `generate_manifests.py --check` first, and on a failed push
it removes the tag it created:

```
task tag:patch
task tag:minor
task tag:major
```

It bumps `version` in `marketplace.config.json`, regenerates the manifest,
commits, tags `vX.Y.Z`, and pushes the commit and tag together. The release is
built from `origin/main`, so uncommitted changes in your checkout are ignored
and never released.

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
not write it. It opens a PR if the branch has none, then waits, within a fixed
budget, for the CI reviewers the repo runs (CodeRabbit when `.coderabbit.yaml`
exists, PR-Agent when `.pr_agent.toml` or a `pr-agent` workflow does) and
resolves their comments. When the repo has none, or none reviews (rate limited,
skipped, slow), it dispatches a local review agent with fresh context (never the
current session) and resolves that agent's findings instead. It reports what
was fixed and declined, and leaves the PR open. If a local reviewer fails, it
tries other viable independent routes. If none works, it reports **BLOCKED**
and stops the calling workflow before merge or release unless the user
explicitly waives review. Self-review and passing tests are not substitutes;
a waiver is reported as **WAIVED**, not reviewed. Other skills, such as `ship`
and `lets-finish`, run it too.

## Lets finish

`/lets-finish` (or "let's finish", "wrap up", "ship it") lands work that is ready. It runs on a small model, so fixes go to the `builder` agent. Words after the command skip or stop steps: `/lets-finish don't review`, `/lets-finish stop after CI`. `/lets-finish and release` also runs the project's release after the merge: its `release` or `deploy` skill, or the process its docs describe. It never releases unless you say so. A branch with no PR gets one,
waits for CI, and goes through `independent-review` first. For each PR it confirms CI
passed and that any required review is done (a CI reviewer or a human), then
squash-merges. It finds the beads, Jira tickets, and GitHub issues the PR
relates to and updates them: closed when the PR closes them, commented when it
only mentions them. It prints one `[+]`, `[-]`, or `[x]` line per step, stops
at the first failed step, and ends by asking `[y/n]` whether to remove the branch and
worktree. It calls the `wait-for-action` and `independent-review` skills. User-invoked only.

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

## Architectural review

`/architectural-review` reviews a codebase's architecture. A script ranks
hotspots (churn × size) and change-coupled files from git history; a
fresh-context agent walks them for friction, judged against a fixed design
vocabulary (module, interface, depth, seam, adapter, locality, leverage) and
the `follow-the-rules` lenses. It renders an HTML report of deepening
candidates with before/after Mermaid diagrams and proposed glossary terms, and
prints the `bd create` commands for an epic plus one bead per candidate, which
it runs only for the candidates you pick. It keeps `GLOSSARY.md`,
`ARCHITECTURE.md`, and `docs/adr/` current as decisions land. Words after the
command name a direction. User-invoked only.
