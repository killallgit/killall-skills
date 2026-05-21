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
