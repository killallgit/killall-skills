---
name: create-rule
description: Create or update an installable reusable rule under `rules/` without mixing it with repository-maintenance instructions.
---

# Create Rule

Use this when the user wants to add a reusable behavioral rule to the
installable payload.

## Workflow

1. Confirm the rule's purpose and when an agent should apply it.
2. Create or update a focused Markdown file under `rules/`.
3. Keep the rule portable: no host-specific config paths, package metadata, or
   generated output assumptions.
4. If the rule depends on current third-party tool behavior, require the agent
   to check latest official docs first and use Context7 MCP when available.
5. Keep examples short and clearly marked as examples.
