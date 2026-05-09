---
name: to-issues
description: Break a plan, spec, or PRD into independently-grabbable issues according to `docs/agents/issue-tracker.md`, using tracer-bullet vertical slices. Use when user wants to convert a plan into issues, create implementation tickets, or break down work into issues.
---

# To Issues

Break a plan into independently-grabbable issues using vertical slices (tracer bullets).

The tracker contract should have been established already — run `/setup-skills` if the repo has not defined `docs/agents/issue-tracker.md` yet.

## Process

### 1. Read the tracker contract

Read `docs/agents/issue-tracker.md` first if it exists. Treat its frontmatter as the contract for where issue slices should be published and which store is canonical. If the file is missing or ambiguous, run `/setup-skills`.

### 2. Gather context

Work from whatever is already in the conversation context. If the user passes a PRD path, issue path, issue number, URL, or issue id as an argument, fetch it from the local workflow first and then from any configured external tracker if needed.

If `canonical_store: external`, fetch the external tracker artifact first and then any local mirror if one exists.

### 3. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. If the repo uses glossary docs, use that vocabulary in issue titles and descriptions. Respect ADRs in the area you're touching.

### 4. Draft vertical slices

Break the plan into **tracer bullet** issues. Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

Slices may be 'HITL' or 'AFK'. HITL slices require human interaction, such as an architectural decision or a design review. AFK slices can be implemented and merged without human interaction. Prefer AFK over HITL where possible.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
</vertical-slice-rules>

### 5. Quiz the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Type**: HITL / AFK
- **Blocked by**: which other slices (if any) must complete first
- **User stories covered**: which user stories this addresses (if the source material has them)

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked as HITL and AFK?

Iterate until the user approves the breakdown.

### 6. Publish the issue files

For each approved slice, publish it according to the tracker contract. Use the template below for any local file representation.

If `canonical_store: local`:

- keep the initiative directory that already contains `PRD.md`
- create numbered issue files like `01-<slug>.md`, `02-<slug>.md`
- publish issues in dependency order so `depends_on` can reference stable ids
- set `status: ready` for AFK slices with no blockers
- set `status: blocked` when the slice is waiting on another issue
- set `status: draft` for HITL slices or slices with unresolved decisions
- if `external_store` is configured, mirror the local issue file outward after the local file exists

If `canonical_store: external`:

- create or update the external issue first
- if `local_store` is configured, update the local mirror after the external issue exists
- keep `external_ref` aligned anywhere a local mirror exists

<issue-template>
---
id: <initiative-slug>-01
title: <issue title>
status: ready
parent: ./PRD.md
depends_on: []
external_ref:
labels: []
---

## Goal

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation.

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Notes

- Record blockers, human decisions, or external references here when needed.

</issue-template>

Do NOT delete or rewrite the parent PRD. The PRD remains the planning contract for the initiative.
