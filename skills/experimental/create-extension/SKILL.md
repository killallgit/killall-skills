---
name: create-extension
description: Create or update a portable agent skill, or a host-registered lifecycle hook, with the correct structure and validation. Use when the user wants to author an installable agent extension in this repository.
---

# Create Extension

Create one of two extension types: a skill or a hook. Confirm the type, name,
trigger conditions, and success criteria before writing files.

## Skill

1. Create or update `skills/<domain>/<name>/SKILL.md`. The domain is one of
   `planning`, `engineering`, `architecture`, `knowledge`, or `experimental`.
2. Add YAML frontmatter with a matching `name` and a precise `description`.
3. Keep the body focused on when to use the skill, what to inspect, the workflow,
   safety constraints, and verification.
4. Keep companion scripts, templates, and references inside the skill directory.
5. Use direct, one-level links from `SKILL.md` for progressive disclosure.

The description is the routing surface. State what the skill does and the
concrete situations that should activate it. Keep it under 1024 characters.

Skills must sit at exactly `skills/<domain>/<name>/SKILL.md`. That is the depth
the cross-agent `skills` CLI walks; a skill nested deeper is not discovered.

## Hook

Hooks here are host-registered side effects, not advisory scripts.

1. Put the hook in its own directory under `hooks/<name>/`, with a README
   covering prerequisites, registration, verification, and uninstall.
2. Check the host's current hook documentation before writing integration
   guidance — payload shapes and hook names change.
3. Read host payloads from environment variables, standard input, or arguments,
   and support a `--dry-run` mode that performs no side effect.
4. Exit successfully when context is missing rather than failing the turn.
5. Never echo untrusted host payload text back to the host as instructions.

Side-effect hooks require explicit user opt-in before registration. Document
that in the hook's README and in `AGENTS.md`.

## Verify

- The directory and frontmatter names match for skills.
- Descriptions distinguish the extension from nearby capabilities.
- Referenced files exist and executable scripts have the executable bit.
- `uv run --with pytest pytest tests -q` passes.
- `npx skills@latest add . --list` shows a new skill at the expected name.

Report the extension type, files changed, validation performed, and assumptions.
