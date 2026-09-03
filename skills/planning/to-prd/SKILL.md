---
name: to-prd
description: Turn the current conversation context into a PRD according to `docs/agents/issue-tracker.md`. Use when user wants to define a piece of work before breaking it into issues.
---

This skill turns the current conversation context and codebase understanding into a PRD.

Do not start with a broad interview. Synthesize first. If something is genuinely ambiguous, ask a narrow clarifying question instead of pretending the plan is settled.

The tracker contract should have been established already — run `/setup-planning` if the repo has not defined `docs/agents/issue-tracker.md` yet.

## Process

1. Read `docs/agents/issue-tracker.md` first if it exists. Treat its frontmatter as the contract for where PRDs live and which store is canonical. If the file is missing or ambiguous, run `/setup-planning`.

2. Explore the repo to understand the current state of the codebase, if you haven't already. If the repo uses glossary docs, use that vocabulary throughout the PRD. Respect any ADRs in the area you're touching.

3. Synthesize the initiative. A PRD in this workflow is the planning contract for a piece of work. It should define:

- the problem
- the desired outcome
- what is in scope
- what is out of scope
- the user stories needed to derive issue slices
- any open questions that block issue breakdown

Do **not** turn the PRD into an architecture doc, module decomposition, or detailed test plan. Those belong later in `to-issues` and `tdd`.

4. If the plan is materially ambiguous, ask only the smallest clarifying question needed to avoid writing the wrong PRD. Otherwise proceed directly.

5. Write the PRD using the template below, then publish it according to the tracker contract.

If `canonical_store: local`:

- choose a concise initiative slug
- create `<local_store>/<initiative-slug>/` if it does not exist
- write the PRD to `<local_store>/<initiative-slug>/PRD.md`
- preserve the existing `id` if you are updating an existing PRD rather than creating a new one
- default `status:` to `draft` unless the user has already explicitly approved the plan
- set `status:` to `approved` only when the user clearly approves the PRD or asks to proceed with issue breakdown
- if `external_store` is configured, mirror the PRD outward after the local PRD exists

If `canonical_store: external`:

- create or update the PRD in the external tracker first
- use the external tracker's issue/ticket artifact as the PRD container unless `docs/agents/issue-tracker.md` says otherwise
- if `local_store` is configured, update the local mirror after the external PRD exists
- set `external_ref` when a local mirror exists

Prefer a concise PRD. Add detail only when it changes scope, slices, or expectations.

<prd-template>

---
id: <initiative-slug>
title: <initiative title>
status: draft
external_ref:
---

## Problem

The problem that the user is facing, from the user's perspective.

## Outcome

The intended result of solving this problem, from the user's perspective.

## In Scope

- Item 1
- Item 2
- Item 3

## User Stories

List the user stories needed to define scope and derive issue slices. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

Do not pad this list for length. Include enough stories to define the initiative cleanly, not every imaginable variation.

## Out of Scope

A description of the things that are out of scope for this PRD.

## Open Questions

- Question 1
- Question 2

Only include questions that materially affect issue breakdown or scope.

## Notes

Any further notes that help the later `to-issues` step, without turning this PRD into a technical implementation spec.

</prd-template>
