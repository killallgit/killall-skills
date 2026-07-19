---
canonical_store: local
local_store: docs/issues
external_store: github
external_ref_prefix: github#
---

# Issue Workflow: GitHub

This template supports either a local-canonical mirror workflow or an external-canonical GitHub workflow.

## Contract

Read the frontmatter in this file before acting:

- `canonical_store: local` means local markdown is authoritative and GitHub mirrors it
- `canonical_store: external` means GitHub is authoritative
- `local_store: docs/issues` means local mirrors exist; leave it blank if the repo does not keep local mirrors
- `external_store: github` means GitHub operations use `gh`
- `external_ref_prefix: github#` is the expected reference prefix

For a GitHub-canonical repo, change the frontmatter to:

```yaml
canonical_store: external
local_store:
external_store: github
external_ref_prefix: github#
```

## Local-canonical rule

When work changes:

1. Create or update the local markdown file under `docs/issues/`
2. Mirror the relevant details to GitHub
3. Record the GitHub issue number in `external_ref`

Example:

```md
---
id: auth-refresh-01
title: Add token refresh path
status: ready
parent: ./PRD.md
depends_on: []
external_ref: github#142
labels: []
---
```

## GitHub operations

- **Create an issue**: `gh issue create --title "..." --body "..."`
- **Read an issue**: `gh issue view <number> --comments`
- **List issues**: `gh issue list --state open --json number,title,labels,comments`
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v`. `gh` does this automatically inside a clone.

## Publishing rule

When a skill says "publish to the issue tracker":

- if `canonical_store: local`, update the local markdown file first and then create or update the GitHub issue
- if `canonical_store: external`, create or update the GitHub issue first and then update any local mirror only if `local_store` is set
- keep `status`, acceptance criteria, and any blocking references aligned

## Fetching rule

When a skill says "fetch the relevant ticket":

- if `canonical_store: local` and the user gives a local path or issue id, read the local file first
- if `canonical_store: external`, read GitHub first
- if the user gives `github#NNN` or `#NNN`, read the GitHub issue and then find or update the matching local file only when `local_store` exists

## Wayfinding operations

Used by `wayfinder`. The **map** is a single issue with **child** issues as tickets. If `canonical_store: local`, the local wayfinding layout from the local template is canonical and these GitHub operations mirror it per the publishing rule; if `canonical_store: external`, these operations are canonical.

- **Map**: a single issue labelled `wayfinder:map`, holding the Destination / Notes / Decisions-so-far / Fog body. `gh issue create --label wayfinder:map`.
- **Child ticket**: an issue linked to the map as a GitHub sub-issue (`gh api` on the sub-issues endpoint). Where sub-issues aren't enabled, add the child to a task list in the map body and put `Part of #<map>` at the top of the child body. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Once claimed, the ticket is assigned to the driving dev.
- **Blocking**: GitHub's **native issue dependencies** — the canonical, UI-visible representation. Add an edge with `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, where `<blocker-db-id>` is the blocker's numeric **database id** (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`, _not_ the `#number` or `node_id`). GitHub reports `issue_dependencies_summary.blocked_by` (open blockers only — the live gate). Where dependencies aren't available, fall back to a `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is unblocked when every blocker is closed.
- **Frontier query**: list the map's open children (`gh issue list --state open`, scoped to the map's sub-issues / task list), drop any with an open blocker (`issue_dependencies_summary.blocked_by > 0`, or an open issue in the `Blocked by` line) or an assignee; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me` — the session's first write.
- **Resolve**: `gh issue comment <n> --body "<answer>"`, then `gh issue close <n>`, then append a context pointer (gist + link) to the map's Decisions-so-far.
