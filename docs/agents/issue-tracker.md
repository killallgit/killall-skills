---
canonical_store: local
local_store: docs/issues
external_store:
external_ref_prefix:
---

# Issue Workflow: Local Markdown

The local source of truth for plans and execution lives under `docs/issues/`.

## Contract

Read the frontmatter in this file before acting:

- `canonical_store: local` means local markdown is authoritative
- `local_store: docs/issues` is where PRDs and issue files live
- `external_store:` empty means there is no external tracker to sync

## Default flow

1. `to-prd` writes `docs/issues/<initiative-slug>/PRD.md`
2. `to-issues` writes numbered issue files in the same directory
3. `tdd` works one issue file at a time and updates `status:` in frontmatter as work progresses

## Layout

```text
docs/
  issues/
    <initiative-slug>/
      PRD.md
      01-<issue-slug>.md
      02-<issue-slug>.md
```

## PRD frontmatter

```md
---
id: auth-refresh
title: Token refresh flow
status: draft
external_ref:
---
```

PRD statuses: `draft`, `approved`, `done`, `superseded`

## Issue frontmatter

```md
---
id: auth-refresh-01
title: Add token refresh path
status: ready
parent: ./PRD.md
depends_on: []
external_ref:
labels: []
---
```

Issue statuses: `draft`, `ready`, `in_progress`, `blocked`, `done`, `wontfix`

## Source of truth rule

The local markdown files are canonical even if this repo later mirrors work to GitHub, GitLab, or another system.

## When a skill says "publish to the issue tracker"

Create or update the local markdown file first under `docs/issues/`. If an external tracker adapter is configured later, mirror the local file outward after the local file exists.

## When a skill says "fetch the relevant ticket"

Read the local file first. The user may pass a file path, initiative slug, frontmatter `id`, or external tracker reference.
