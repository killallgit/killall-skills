---
name: project-planner
description: Turn a fuzzy software idea into a project-level brief — milestones, vertical-slice action items, non-goals, and risks. Use when a user wants to plan an app, feature set, rewrite, or backlog, and needs to decide what gets built and in what order before any single feature gets a spec.
---

# Project Planner

Use when the user has a fuzzy software idea and wants a plan before anything is
specced. This is **project-level**: what gets built, in what order, and what
does not get built. Upstream `to-spec` writes the spec for one feature; this
decides which features earn one.

## Interview with `grilling`

Do not improvise a question list. Run the interview with the `grilling` skill —
a design tree worked one frontier round at a time, each round's answers pushing
the frontier outward. Its two rules matter most here:

- **Facts are yours to find.** Dispatch a sub-agent for anything in the
  environment. Only decisions go to the user.
- **Nothing silently assumed.** A gap you paper over becomes a milestone that
  sequences wrong.

## Coverage

The plan cannot be written until these are settled. They are slots the output
needs filled, not a script to read out — `grilling` decides the order:

- Intent: what are we building, and why should it exist?
- Users: who uses it, administers it, buys it, or is affected by it?
- Success: what outcome proves the project worked?
- Workflows: the 3-5 most important things users must do.
- Scope: must-have, nice-to-have, and explicit non-goals.
- Domain model: important objects, records, states, and events.
- Interfaces: web, mobile, CLI, API, jobs, integrations, admin tools.
- Constraints: stack, hosting, auth, budget, timeline, data, compliance.
- Risks: unknown APIs, hard UX, migrations, scale, security, operations.
- Delivery shape: prototype, MVP, production release, migration, or experiment.

## Planning Rules

- Do not jump straight from a vague idea to a backlog.
- Slice vertically: user-visible behavior cutting across UI, data, logic,
  integrations, and tests. Avoid layer-only tasks like "build backend", "make
  UI", or "set up database" unless they are genuinely standalone enabling work.
- Order by learning value and user value, not technical layering.
- Keep the final plan readable in under five minutes.
- If the plan feels large, split work into `Now`, `Next`, and `Later`.
- Stop at the plan. Each action item that survives goes to the spec-writing
  skill (upstream `to-spec`) on its own; ticket breakdown is `to-tickets`' job.

## Final Output

Use this structure unless the user asks for a different artifact:

```markdown
## Project Brief

<3-5 concise sentences>

## Non-Goals

- <things intentionally excluded>

## Core Workflows

- <workflow>
- <workflow>
- <workflow>

## Key Objects

- `<object>`: <why it matters>

## Milestones

1. <milestone name>: <outcome>
2. <milestone name>: <outcome>
3. <milestone name>: <outcome>

## Actionable Items

1. <vertical slice task>
2. <vertical slice task>
3. <vertical slice task>

## Validation

- <manual smoke, automated test, metric, or demo condition>

## Risks And Decisions

- <risk or decision>
```
