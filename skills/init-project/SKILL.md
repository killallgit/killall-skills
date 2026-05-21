---
name: init-project
description: Initialize a repository to use this tool-agnostic skill pack by inspecting local context, linking or copying skills and hooks, and preserving existing user config.
---

# Init Project

Use this when a user wants to integrate this repository into another project or
agent host without adopting a package-manager-specific workflow.

## Workflow

1. Inspect the target project and identify existing agent instructions, skills,
   hooks, rules, and config files.
2. Check the latest documentation for the target host before changing config or
   hook wiring.
3. Prefer symlinks for local development and copies for portable installs.
4. Preserve user-owned config. If a merge is needed, show the planned change,
   back up the original file, and use a structured parser where possible.
5. Verify the target host can discover the installed skills and hooks.
6. Report exactly what was linked, copied, merged, skipped, or left for manual
   follow-up.
