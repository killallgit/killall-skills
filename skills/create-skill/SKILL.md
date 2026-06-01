---
name: create-skill
description: Create or update an installable skill under `skills/` with valid frontmatter, scoped instructions, and any companion files it needs.
---

# Create Skill

Use this when the user wants to add or revise a reusable skill in this
repository's installable payload.

## Workflow

1. Confirm the intended skill name, trigger conditions, and success criteria.
2. Create or update `skills/<skill-name>/SKILL.md`.
3. Add YAML frontmatter with `name` and `description`.
4. Keep the body focused on agent behavior: when to use it, what to inspect,
   what steps to follow, and how to verify the outcome.
5. Put companion templates, scripts, and references inside the same skill
   directory.
6. Do not add host-specific package metadata or assume a specific coding tool.
7. Report the files changed and any assumptions the skill makes.

## Description

The description is the trigger surface. The agent sees it before the skill body,
so make it specific enough to choose this skill instead of nearby skills.

- First sentence: what capability the skill provides.
- Second sentence: `Use when ...` with concrete triggers, phrases, or contexts.
- Keep it under 1024 characters.
- Avoid vague descriptions like "helps with engineering work".

Good:

```yaml
description: Run a red-green-refactor loop against one issue contract. Use when the user asks for TDD, test-first work, or to implement a ready issue slice.
```

Bad:

```yaml
description: Helps write code.
```

## Companion Files

Use progressive disclosure:

- Keep `SKILL.md` as the core workflow, preferably under 100 lines.
- Split detailed variants into one-level reference files, such as
  `LOGIC.md`, `UI.md`, or `GITHUB.md`.
- Add `scripts/` only for deterministic operations that would otherwise be
  rewritten repeatedly, such as validation, parsing, or hook checks.
- Do not add `README.md`, changelogs, install guides, or process notes inside a
  skill directory.

After updating a skill, verify:

- [ ] Description includes clear trigger conditions.
- [ ] References are linked directly from `SKILL.md`.
- [ ] Scripts are executable when intended to be run.
- [ ] No host-specific plugin metadata was added under `skills/`.
