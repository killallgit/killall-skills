---
name: agent-setup
description: Set up, or remove, an orchestrator session role plus builder, reviewer, and hall-monitor agents in a repository for Claude Code, Codex, and Cursor.
disable-model-invocation: true
argument-hint: "[remove] [path]"
---

# Agent setup

Give a repository an orchestrator that every session starts as, and the three lane agents it runs: `builder`, `reviewer`, and `hall-monitor`. Everything comes from `templates/`, filled with what this repository actually uses.

When the first argument is `remove`, run `python3 scripts/render_agents.py --dest <git-root> --remove` from this skill's directory and report what it removed. It deletes only what carries the agent-setup marker, including what earlier versions wrote.

## 1. Look

Work in the path the user gave, otherwise `git rev-parse --show-toplevel`. Record each value from the repository, not from memory. Install nothing, and ask only where a row says so.

| Value | Where it comes from |
| --- | --- |
| hosts | Each of `claude`, `codex`, `cursor` whose folder (`.claude/`, `.codex/`, `.cursor/`) exists in the repository or the home directory; all three when none does |
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

Write the values to a temporary JSON file outside the repository, then from this skill's directory:

```bash
python3 scripts/render_agents.py --dest <git-root> --vars <temp.json> --hosts <hosts>
```

Per host it writes the three agents, plus the orchestrator and the setting that makes a session start as it:

| Host | Agents | Orchestrator |
| --- | --- | --- |
| Claude Code | `.claude/agents/*.md` | `.claude/agents/orchestrator.md`, and `"agent": "orchestrator"` in `.claude/settings.json` |
| Codex | `.codex/agents/*.toml` | A marked `developer_instructions` block at the top of `.codex/config.toml` |
| Cursor | `.cursor/agents/*.md` | `.cursor/rules/orchestrator.mdc`, always applied |

A rerun replaces what it wrote and clears what earlier versions wrote, including old instruction blocks. It refuses to touch a file, `agent` setting, or `developer_instructions` key it did not write, and writes nothing; ask the user before rerunning with `--force`.

Done when the script exits 0.

## 3. Check

- Every written file exists and has no `{{` left.
- `follow-the-rules` resolves on each host: a `follow-the-rules/SKILL.md` under `.claude/skills/`, `.agents/skills/`, or `.cursor/skills/`, the same folders under `~`, or an enabled plugin that ships it. Builder and hall-monitor depend on it.
- Codex loads project config and `.codex/agents/` only for a trusted project: check `~/.codex/config.toml`.
- Codex builders inherit the main session's sandbox, so they write only when the session runs `workspace-write`. When worktrees live outside the git root, that sandbox blocks them too; the ways out are the `.worktrees/` location or the worktree folder added to `sandbox_workspace_write.writable_roots` in `~/.codex/config.toml`.

## 4. Report

Tell the user: the hosts, the gate, the worktree note, the files written, and how a session starts as the orchestrator on each host: `claude` (or `claude --agent orchestrator`), `codex` in the trusted project, and Cursor's agent in the repository. Name each host where `follow-the-rules` did not resolve, and any Codex trust or sandbox gap. The files are ordinary tracked files; committing them is the user's call, and `/agent-setup remove` takes them out again.
