---
name: project-planner
description: Systematic software-project scoping interviewer that turns fuzzy ideas into concise briefs, milestones, and vertical-slice action items. Use when a user wants to plan an app, feature, rewrite, prototype, or backlog before PRD/issue/TDD work begins.
---

# Project Planner

Use this when the user has a fuzzy software idea and wants a concise,
actionable plan before implementation. This skill sits before `to-prd` and
`to-issues`: interview first, then hand off a clear brief or backlog.

## Interview Contract

Cover these slots before producing the final plan:

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

## Process

1. Ask a framing batch of 3-6 questions. Prefer concrete options over abstract
   prompts. If the user asks for one question at a time, switch to that mode.
2. Ask a workflow batch: core flows, unhappy paths, and what can be cut.
3. Ask a system-shape batch: data, interfaces, auth, integrations, import/export,
   notifications, and operational expectations.
4. Summarize the current understanding, then ask only gap questions that would
   materially change the plan.
5. Produce the final plan using vertical slices: user-visible behavior that cuts
   across UI, data, logic, integrations, and tests where applicable.

Keep momentum. If an answer is missing but low-risk, state an assumption and
continue. Challenge ambiguity gently when it would change scope or sequencing.

## Planning Rules

- Do not jump straight from a vague idea to a backlog.
- Avoid layer-only tasks like "build backend", "make UI", or "set up database"
  unless they are genuinely standalone enabling work.
- Order by learning value and user value, not technical layering.
- Keep the final plan readable in under five minutes.
- If the plan feels large, split work into `Now`, `Next`, and `Later`.
- If the user wants tickets, convert action items into independently grabbable
  issues with acceptance criteria, or hand off to `to-issues`.

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
