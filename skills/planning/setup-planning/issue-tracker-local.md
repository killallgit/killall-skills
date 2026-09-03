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

One initiative per directory. Keep the PRD and its derived issue files together.

## PRD frontmatter

Use YAML frontmatter on `PRD.md`:

```md
---
id: auth-refresh
title: Token refresh flow
status: draft
external_ref:
---
```

- `id` — stable initiative identifier
- `title` — human-readable title
- `status` — one of `draft`, `approved`, `done`, `superseded`
- `external_ref` — optional external tracker reference such as `github#142`

## Issue frontmatter

Use YAML frontmatter on issue files:

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

- `id` — stable issue identifier
- `title` — human-readable issue title
- `status` — one of `draft`, `ready`, `in_progress`, `blocked`, `done`, `wontfix`
- `parent` — usually `./PRD.md`
- `depends_on` — list of sibling issue ids that must finish first
- `external_ref` — optional external tracker reference
- `labels` — optional extra metadata for future integrations

## Body sections

PRDs should keep their planning sections in the markdown body.

Issue files should usually include:

- `## Goal`
- `## Acceptance Criteria`
- `## Notes`

## Source of truth rule

The local markdown files are canonical even if the repo later mirrors work to GitHub, GitLab, or another system.

## When a skill says "publish to the issue tracker"

Create or update the local markdown file first under `docs/issues/`. If an external tracker adapter is configured, mirror the local file outward after the local file exists.

## When a skill says "fetch the relevant ticket"

Read the local file first. The user may pass:

- the file path
- the initiative slug
- the frontmatter `id`
- the external tracker reference

## Wayfinding operations

Used by `wayfinder`. The **map** is a file with one **child** file per ticket, using the same layout and frontmatter machinery as an initiative.

- **Map**: `docs/issues/<effort-slug>/map.md` — frontmatter `labels: [wayfinder:map]`; body holds Destination / Notes / Decisions-so-far / Not-yet-specified / Out-of-scope.
- **Child ticket**: `docs/issues/<effort-slug>/NN-<slug>.md`, numbered from `01`. Frontmatter: `parent: ./map.md`, `labels: [wayfinder:<type>]` (`research`/`prototype`/`discussion`/`task`), `depends_on:` listing sibling ids, and `status:`. The body is the `## Question`.
- **Blocking**: `depends_on` — a ticket is unblocked when every sibling it lists is `done`.
- **Frontier**: scan the effort directory for tickets with `status: ready` whose `depends_on` is empty or fully `done`; first by number wins.
- **Claim**: set `status: in_progress` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `status: done`, then append a context pointer (gist + link) to the map's Decisions-so-far.
- **Out of scope**: set `status: wontfix` and add the one-line gist plus reason to the map's Out-of-scope section.
