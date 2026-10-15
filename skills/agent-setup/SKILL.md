---
name: agent-setup
description: Set up, or remove, an orchestrator session role plus builder, reviewer, and hall-monitor agents in a repository for Claude Code, Codex, and Cursor.
disable-model-invocation: true
argument-hint: "[remove] [path]"
---

# Agent setup

Give a repository an orchestrator every session starts as, and its three lane agents, rendered from `templates/` with this repository's values.

When the first argument is `remove`, run `python3 scripts/render_agents.py --dest <git-root> --remove` from this skill's directory and report what it removed.

## 1. Look

Use the given path, otherwise `git rev-parse --show-toplevel`. Discover values from the repository. Install nothing; ask only where specified.

| Value | Where it comes from |
| --- | --- |
| hosts | Each of `claude`, `codex`, `cursor` whose folder (`.claude/`, `.codex/`, `.cursor/`) is in the repository or home directory; all three when none is |
| `project` | One sentence from the README or package manifest: what the repo is and its main parts |
| `conventions` | The instruction file holding the repo's rules, such as `` `AGENTS.md` ``; otherwise `the patterns already in the code` |
| `gate` | The check a pull-request workflow runs; otherwise one of `task check`, `make check`, `just check`, `npm test`, `pnpm test`, `cargo test`, `go test ./...`, `pytest`. Ask when two are equally plausible |
| `gate_scopes` | Optional. One sentence naming a smaller check per area, when the repo defines one |
| `default_branch` | `origin/HEAD`, else the branch the user names |
| `worktree_note` | The three sentences below |

The worktree note, from `AGENTS.md`, `CLAUDE.md`, the git hooks, and `git worktree list`:

1. "Worktrees are created with `<command>` at `<location>`. Before the first edit, confirm you are on the branch the brief names, in the worktree it names." With no pattern found: "Create each worktree with `git worktree add <git-root>/.worktrees/<lane> -b lane/<lane> <default_branch>`, after adding `.worktrees/` to `.git/info/exclude` once.", with the real git root and default branch.
2. The repo's branch and commit message rules, or "Branches are named `lane/<name>`. Each commit message is one plain sentence."
3. The repo's merge rule, or "Integrate by rebasing the lane onto the default branch, running the gate, and fast-forwarding."

Done when every value names something you found, or its stated fallback.

## 2. Write

Write the values to a JSON file outside the repository, then from this skill's directory:

```bash
python3 scripts/render_agents.py --dest <git-root> --vars <temp.json> --hosts <hosts>
```

Templates hold role instructions, tools, models, and effort; the renderer adapts them to native files and locally excludes generated paths from Git. It creates a shared state README under `~/.config/killall-skills/agents/state/<encoded-main-checkout>/` (honoring `XDG_CONFIG_HOME`). Reruns refresh definitions and the README, preserve lane JSON, and clear legacy output. Update the installed skill first for newer agents. Ask before using `--force` on refused foreign files or settings.

Done when the script exits 0.

## 3. Check

- `follow-the-rules`, which builder and hall-monitor load, resolves on each host: under `.claude/skills/`, `.agents/skills/`, or `.cursor/skills/` in the repository or `~`, or from an enabled plugin.
- Codex needs a trusted project and write access to worktrees and the printed state folder (`codex --add-dir <state-folder>`). Subagents inherit session permissions. Its orchestrator delegates by instruction; Claude's tool allowlist excludes shell and edit tools.

## 4. Report

Report hosts, models/effort, gate, worktree note, files and state folder, and startup commands. Report unresolved `follow-the-rules`, tracked generated files (local excludes cannot untrack them), and Codex's isolation limit. `/agent-setup remove` removes definitions and local excludes while preserving lane state.
