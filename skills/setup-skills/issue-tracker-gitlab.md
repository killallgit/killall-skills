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
