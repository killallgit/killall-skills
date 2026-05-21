---
name: init-project
description: Initialize a repository to use this tool-agnostic skill pack by integrating only the installable payload and preserving existing user config.
---

# Init Project

Use this when a user wants to integrate this repository's installable `payload/`
into another project or agent host without adopting a package-manager-specific
workflow.

## Workflow

1. Inspect the target project and identify existing agent instructions, skills,
   hooks, rules, and config files.
2. Check the latest documentation for the target host before changing config or
   hook wiring. Use Context7 MCP first when available.
3. Treat `payload/` as the only installable source. Do not install root-level
   repository-maintenance files.
4. Prefer symlinks for local development and copies for portable installs.
5. Preserve user-owned config. If a merge is needed, show the planned change,
   back up the original file, and use a structured parser where possible.
6. Verify the target host can discover the installed skills, rules, and hooks.
7. Report exactly what was linked, copied, merged, skipped, or left for manual
   follow-up.
