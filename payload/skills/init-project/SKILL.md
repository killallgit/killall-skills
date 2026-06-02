---
name: init-project
description: Install this skill pack's skills, rules, and hooks into a target project or agent host, preserving existing user config. Use when a user wants to wire killall-skills into their coding tool.
---

# Init Project

Install the content of this repo (`skills/`, `rules/`, `hooks/`) into a target
coding tool. There is no package manager — you do the wiring by hand.

## Workflow

1. Read this repo's `AGENTS.md` — it has the per-host install recipe.
2. Inspect the target: existing agent instructions, skills, rules, hooks, config.
3. Check the host tool's latest docs before changing config or hook wiring. Use
   Context7 MCP first when available.
4. Follow the `AGENTS.md` procedure: prefer symlinks for local dev, copies for
   portable installs; back up any config before editing; preserve user-owned config.
5. Verify the host discovers the installed skills, rules, and hooks.
6. Report exactly what was linked, copied, merged, skipped, or left for manual
   follow-up.
