---
name: create-extension
description: Create or update a portable agent skill, reusable behavioral rule, or lifecycle hook with the correct structure and validation. Use when the user wants to author an installable agent extension in this repository.
---

# Create Extension

Create one of three extension types: a skill, rule, or hook. Confirm the type,
name, trigger conditions, and success criteria before writing files.

## Skill

1. Create or update `plugins/<domain>/skills/<name>/SKILL.md`.
2. Add YAML frontmatter with a matching `name` and a precise `description`.
3. Keep the body focused on when to use the skill, what to inspect, the workflow,
   safety constraints, and verification.
4. Keep companion scripts, templates, and references inside the skill directory.
5. Use direct, one-level links from `SKILL.md` for progressive disclosure.

The description is the routing surface. State what the skill does and the
concrete situations that should activate it. Keep it under 1024 characters.

## Rule

1. Create or update one focused Markdown file under `rules/`.
2. Describe when the behavior applies and what the agent must do.
3. Keep the rule portable and separate from repository-maintenance instructions.
4. If it depends on current third-party behavior, require checking current
   official documentation before acting.

## Hook

1. Choose the lifecycle phase: `pre-session`, `pre-tool`, `post-tool`, or
   `post-session`.
2. Check the host's current hook documentation before writing integration
   guidance.
3. Put host-neutral advisory scripts under `hooks/<phase>/` with a numeric prefix.
4. Read host payloads from environment variables, standard input, or arguments.
5. Never echo untrusted host payloads as `HOOK_INSTRUCTION:`. Emit only
   repository-authored guidance and exit successfully when context is missing.

Host-registered side-effect hooks remain separate and require explicit user
opt-in before registration.

## Verify

- The directory and frontmatter names match for skills.
- Descriptions distinguish the extension from nearby capabilities.
- Referenced files exist and executable scripts have the executable bit.
- Host-specific package metadata stays in the owning plugin root.
- The relevant manifest, hook, or repository tests pass.

Report the extension type, files changed, validation performed, and assumptions.
