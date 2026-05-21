---
name: create-skill
description: Create or update an installable skill under `payload/skills/` with valid frontmatter, scoped instructions, and any companion files it needs.
---

# Create Skill

Use this when the user wants to add or revise a reusable skill in this
repository's installable payload.

## Workflow

1. Confirm the intended skill name, trigger conditions, and success criteria.
2. Create or update `payload/skills/<skill-name>/SKILL.md`.
3. Add YAML frontmatter with `name` and `description`.
4. Keep the body focused on agent behavior: when to use it, what to inspect,
   what steps to follow, and how to verify the outcome.
5. Put companion templates, scripts, and references inside the same skill
   directory.
6. Do not add host-specific package metadata or assume a specific coding tool.
7. Run `bash scripts/validate.sh`.
8. Report the files changed and any assumptions the skill makes.
