# Serena and factory lanes

Read this when step 4 finds Serena: a `serena` MCP server in any host's config, or `.serena/project.yml` in the repository.

## Why it needs care

Serena binds one project root when its process starts. With `--project-from-cwd` it takes the nearest boundary above its working directory, and a worktree's own `.git` file wins over the primary checkout's `.serena/project.yml`. A Serena started inside a worktree therefore serves that worktree correctly.

Factory lanes run as subagents. A subagent shares its parent's MCP servers, so its Serena is still bound to the primary checkout. Its reads show the primary checkout's code, and its symbolic edits land there, with nothing to warn the lane. Rebinding with `activate_project` would move the parent's Serena too, which breaks every other lane running at the same time. Upstream treats this as a host limitation: oraios/serena#1496.

So the factory uses Serena where it is bound correctly: the orchestrator, and read-only exploration, in the primary checkout. Builder lanes leave it unused.

## Check

Record each finding for the report. Change nothing here unless the user asks.

1. Launch flags, per host:
   - Claude Code: `claude mcp get serena`.
   - Codex: `[mcp_servers.serena]` in `~/.codex/config.toml` and `.codex/config.toml`.
   - Cursor: the `serena` entry in `~/.cursor/mcp.json` and `.cursor/mcp.json`.

   Each should carry `--project-from-cwd`. A fixed `--project <path>` binds every session, even one started inside a worktree, to that path; report it.
2. Project files: `.serena/project.yml` and `.serena/memories/` reach a worktree only when they are tracked. Serena's own `.serena/.gitignore` keeps `cache` and `project.local.yml` out. When they are untracked, report that a worktree session gets Serena's defaults and no memories.
3. Hooks: list every hook that runs `serena-hooks`, in each host's settings. `remind` runs before tool calls and, after a run of plain reads or searches, denies one call and points the agent at Serena's tools. Hooks fire inside subagents too, and none of them looks at the working directory. In a lane, that nudge points at the Serena bound to the primary checkout.

## What goes into `isolation_note`

Append:

"Leave Serena unused in this worktree. It is bound to the primary checkout, so its reads show that checkout and its edits land there. A hook may deny a read or search and suggest Serena; repeat the call with the built-in file tools."

## Report

Name each host's launch flags and whether they bind per working directory, whether `.serena/` is tracked, and the Serena hooks found. State that lanes leave Serena unused and the orchestrator keeps it.
