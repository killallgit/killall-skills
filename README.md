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

`/factory-builder` (`$factory-builder` in Codex) sets a repository up to run
work as parallel sub-agent lanes, each in its own git worktree, with the
orchestrator checking every lane's gate and diff before it lands. It follows
what the repository already uses: a structure tool such as gstack,
mattpocock/skills, agent-skills, or Spec Kit owns specs and reviews when one is
installed, and the factory's own spec, review, and approve loop fills in when
none is. It installs no structure tool. It records the repository's git and
worktree rules, and when Serena is configured it keeps lanes off Serena, which
stays bound to the main checkout. Agents are generated for Claude Code, Codex,
and Cursor. `/factory-builder uninstall` removes everything it added.
User-invoked only.

## Git janitor

In Claude Code, `/git-janitor` cleans the current repository. Pass a path to
target another repository, or add `audit-only` to inspect without removing
anything. The plugin-qualified command is `/killall-skills:git-janitor`.

For a separate conversation context, ask Claude Code to use the
`killall-skills:git-janitor` agent and include the repository path and any
scope limits. The agent uses the same skill and returns a cleanup receipt.
Its context is separate; it operates on the repository's actual worktrees.
