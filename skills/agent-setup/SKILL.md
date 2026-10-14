---
name: agent-setup
description: Set up an orchestrate skill plus builder, reviewer, and hall-monitor agents in a repository for Claude Code, Codex, and Cursor, and wire them into its instruction files so its development framework hands parallel work to them, or remove them again.
disable-model-invocation: true
argument-hint: "[remove] [path]"
---

# Agent setup

Give a repository one skill and three agents:

- `orchestrate` is a skill the main session runs. It cuts a spec or plan into lanes, runs one `builder` per lane in parallel, each in its own git worktree, has every lane checked, and verifies it before it lands. It writes no product code. It is a skill, not an agent, because a subagent cannot start further subagents.
- `builder` implements one lane in its worktree, following the `follow-the-rules` skill, and runs the gate.
- `reviewer` independently checks a lane against its spec: acceptance checks, tests, callers, and trust boundaries. It may run the gate and tests, and changes no code.
- `hall-monitor` checks a lane against the `follow-the-rules` skill and the codebase's established patterns. Read-only.

The loop: spec or plan, lanes, builders in parallel, the main session's own gate and diff check, then a reviewer and a hall-monitor per lane in parallel, findings back to the same builder for at most two rounds, and integration only when the user asks.

Everything comes from `templates/`, filled with what this repository actually uses. `agents/openai.yaml` next to this file keeps Codex from invoking this skill on its own.

When the first argument is `remove`, run `python3 scripts/render_agents.py --dest <git-root> --remove` from this skill's directory and report what it removed. It deletes only files and instruction blocks that carry the agent-setup marker, including the `orchestrator` agent earlier versions wrote. An instruction file left empty is deleted.

## 1. Look

Work in the path the user gave, otherwise `git rev-parse --show-toplevel`. Record these from the repository, not from memory. Install nothing and ask nothing, except where a step says so.

| Value | Where it comes from |
| --- | --- |
| hosts | `claude`, `codex`, `cursor`: each host whose folder (`.claude/`, `.codex/`, `.cursor/`) exists in the repository or the home directory, or all three when none does |
| `project` | One sentence from the README or package manifest: what the repo is and its main parts |
| `conventions` | The instruction file that holds the repo's rules, such as `` `AGENTS.md` ``; otherwise `the patterns already in the code` |
| `gate` | The check a pull-request workflow runs; otherwise one of `task check`, `make check`, `just check`, `npm test`, `pnpm test`, `cargo test`, `go test ./...`, `pytest`. Ask when two are equally plausible |
| `gate_scopes` | Optional. One sentence naming a smaller check per area when the repo defines one |
| `default_branch` | `origin/HEAD`, else the branch the user names |
| `worktree_note` | The worktree note below |

### Worktree note

Read `AGENTS.md`, `CLAUDE.md`, the git hooks, and `git worktree list`. The note is instructions to the main session and every builder:

1. "Worktrees are created with `<command>` at `<location>`. Before the first edit, confirm you are on the branch the brief names, in the worktree it names." With no pattern found, the first sentence is "Create each worktree with `git worktree add <git-root>/.worktrees/<lane> -b lane/<lane> <default_branch>`, after adding `.worktrees/` to `.git/info/exclude` once.", with the real git root and default branch filled in.
2. The branch naming and commit message rules the repo states, one sentence each, or "Branches are named `lane/<name>`. Each commit message is one plain sentence."
3. The merge rule the repo states, or "Integrate by rebasing the lane onto the default branch, running the gate, and fast-forwarding."

When the hosts include `codex` and the repo's worktrees live outside the git root, Codex's `workspace-write` sandbox blocks a builder's writes there. Report it with both ways out: the `.worktrees/` location above, or the worktree folder added to `sandbox_workspace_write.writable_roots` in `~/.codex/config.toml`.


Done when every value has an entry and each names something you found, or its stated fallback.

## 2. Write

Write the values to a temporary JSON file outside the repository. From this skill's directory:

```bash
python3 scripts/render_agents.py --dest <git-root> --vars <temp.json> --hosts <hosts>
```

For each host given, the script writes the three agents into `.claude/agents/`, `.codex/agents/`, or `.cursor/agents/`, and the `orchestrate` skill into `.claude/skills/`, `.agents/skills/`, or `.cursor/skills/`. It deletes an `orchestrator` agent an earlier version wrote. Rerunning replaces what it wrote before. It refuses to overwrite an agent or skill file it did not write; ask the user before rerunning with `--force`.

Done when the script exits 0.

## 3. Check

- Each agent and skill file exists for each host and has no `{{` left.
- `follow-the-rules` resolves on each host: a `follow-the-rules/SKILL.md` under `.claude/skills/`, `.agents/skills/`, or `.cursor/skills/`, the same folders under `~`, or an enabled plugin that ships it. The builder and hall-monitor depend on it, and hall-monitor returns `rules unavailable` without it. When it is missing on a host, report that host.
- Codex loads `.codex/agents/` only for a trusted project; say so when this project is not trusted in `~/.codex/config.toml`.

## 4. Report

Tell the user the hosts, the gate, the worktree note, any Codex sandbox gap, where `follow-the-rules` resolved and where it did not, and the files written. The files are ordinary tracked files; committing them is the user's call. `/agent-setup remove` takes them out again.
