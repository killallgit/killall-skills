---
canonical_store: local
local_store: docs/issues
external_store: gitlab
external_ref_prefix: gitlab#
---

# Issue Workflow: GitLab

This template supports either a local-canonical mirror workflow or an external-canonical GitLab workflow.

## Contract

Read the frontmatter in this file before acting:

- `canonical_store: local` means local markdown is authoritative and GitLab mirrors it
- `canonical_store: external` means GitLab is authoritative
- `local_store: docs/issues` means local mirrors exist; leave it blank if the repo does not keep local mirrors
- `external_store: gitlab` means GitLab operations use `glab`
- `external_ref_prefix: gitlab#` is the expected reference prefix

For a GitLab-canonical repo, change the frontmatter to:

```yaml
canonical_store: external
local_store:
external_store: gitlab
external_ref_prefix: gitlab#
```

## Local-canonical rule

When work changes:

1. Create or update the local markdown file under `docs/issues/`
2. Mirror the relevant details to GitLab
3. Record the GitLab issue number in `external_ref`

Example:

```md
---
id: auth-refresh-01
title: Add token refresh path
status: ready
parent: ./PRD.md
depends_on: []
external_ref: gitlab#142
labels: []
---
```

## GitLab operations

- **Create an issue**: `glab issue create --title "..." --description "..."`
- **Read an issue**: `glab issue view <number> --comments`
- **List issues**: `glab issue list --state opened -F json`
- **Comment on an issue**: `glab issue note <number> --message "..."`
- **Apply / remove labels**: `glab issue update <number> --label "..."` / `--unlabel "..."`
- **Close**: `glab issue close <number>`

Infer the repo from `git remote -v`. `glab` does this automatically inside a clone.

## Publishing rule

When a skill says "publish to the issue tracker":

- if `canonical_store: local`, update the local markdown file first and then create or update the GitLab issue
- if `canonical_store: external`, create or update the GitLab issue first and then update any local mirror only if `local_store` is set
- keep `status`, acceptance criteria, and any blocking references aligned

## Fetching rule

When a skill says "fetch the relevant ticket":

- if `canonical_store: local` and the user gives a local path or issue id, read the local file first
- if `canonical_store: external`, read GitLab first
- if the user gives `gitlab#NNN` or a GitLab issue number, read the GitLab issue and then find or update the matching local file only when `local_store` exists

## Wayfinding operations

Used by `wayfinder`. The **map** is a single issue with **child** issues as tickets. If `canonical_store: local`, the local wayfinding layout from the local template is canonical and these GitLab operations mirror it per the publishing rule; if `canonical_store: external`, these operations are canonical.

- **Map**: a single issue labelled `wayfinder:map`, holding the Destination / Notes / Decisions-so-far / Fog body. `glab issue create --label wayfinder:map`. (On GitLab tiers with native epics, an epic may hold the map instead; a labelled issue works everywhere.)
- **Child ticket**: an issue carrying `Part of #<map>` at the top of its description and labels `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Once claimed, the ticket is assigned to the driving dev.
- **Blocking**: GitLab's **native blocking link** — the canonical, UI-visible representation. Add it with the `/blocked_by #<n>` quick action, posted as a note (`glab issue note <child> --message "/blocked_by #<blocker>"`). Native blocking links are a Premium/Ultimate feature; on the free tier (or where unavailable) fall back to a `Blocked by: #<n>, #<n>` line at the top of the description. A ticket is unblocked when every blocker is closed.
- **Frontier query**: `glab issue list -F json` scoped to the map's children, drop any with an open blocker — a native `blocked_by` link to an open issue (`glab api projects/:id/issues/:iid/links`), or an open issue in the `Blocked by` line — or an assignee; first in map order wins.
- **Claim**: `glab issue update <n> --assignee @me` — the session's first write.
- **Resolve**: `glab issue note <n> --message "<answer>"`, then `glab issue close <n>`, then append a context pointer (gist + link) to the map's Decisions-so-far.
