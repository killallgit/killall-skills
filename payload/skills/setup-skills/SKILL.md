---
name: setup-skills
description: Sets up a PRD -> issues -> TDD workflow, with `docs/agents/issue-tracker.md` declaring whether local files or an external tracker are canonical. Run before first use of `to-prd`, `to-issues`, `tdd`, or `triage` when a repo has not established its planning workflow yet.
---

# Setup Core Skills

Scaffold the per-repo workflow the engineering skills assume:

- **Plans and work items** — local markdown under `docs/issues/` when the repo uses local files at all
- **Tracker contract** — `docs/agents/issue-tracker.md` declares whether local files or an external tracker are canonical
- **External tracker adapter** — optional GitHub, GitLab, or other rules recorded under `docs/agents/`
- **Decision docs** — optional ADRs under `docs/adr/`, created lazily when the repo actually needs them
- **Optional context docs** — `docs/CONTEXT.md` or `docs/CONTEXT-MAP.md`, created lazily by design-focused skills only when the extra vocabulary discipline is useful

This is a prompt-driven skill, not a deterministic script. Explore, present what you found, confirm with the user, then write.

## Process

### 1. Explore

Look at the current repo to understand its starting state. Read whatever exists; don't assume:

- `git remote -v` and `.git/config`
- agent instruction files at the repo root
- `docs/issues/`
- `docs/agents/`
- `docs/adr/`
- `docs/CONTEXT.md` and `docs/CONTEXT-MAP.md`
- `docs/out-of-scope/`

### 2. Present findings and ask

Summarise what's present and what's missing. Then walk the user through the decisions **one at a time**. Do not dump every decision at once.

Assume the user does not know the vocabulary yet. Each section starts with a short explainer, then the recommended default.

**Section A — Planning workflow.**

> Explainer: this skill set always follows the same conceptual path — `to-prd` -> `to-issues` -> `tdd` — but the canonical store may be local markdown, an external tracker, or a local+external mirror. The repo needs to declare which store is authoritative.

Recommended default:

```text
docs/
  issues/
    <initiative-slug>/
      PRD.md
      01-<issue-slug>.md
      02-<issue-slug>.md
  adr/                      # optional, created lazily
  CONTEXT.md                # optional, created lazily
  CONTEXT-MAP.md            # optional, created lazily
  out-of-scope/             # optional, created lazily
```

Explain the status model:

- PRDs use `draft`, `approved`, `done`, `superseded`
- Issue files use `draft`, `ready`, `in_progress`, `blocked`, `done`, `wontfix`

Explain the file flow:

- `to-prd` writes `docs/issues/<initiative-slug>/PRD.md`
- `to-issues` writes numbered issue files in the same directory
- `tdd` works one issue at a time and updates the issue file status

Ask whether the repo should use that default local workflow.

**Section B — External tracker adapter.**

> Explainer: an external tracker is optional. If the repo uses GitHub or GitLab, we still need to know whether it is only a mirror or whether it is the canonical source of truth.

Default posture: **local only**.

Offer:

- **Local only** — no external tracker adapter
- **GitHub mirror** — local markdown is canonical, GitHub is mirrored via `gh`
- **GitHub canonical** — GitHub is canonical, local files are absent or secondary
- **GitLab mirror** — local markdown is canonical, GitLab is mirrored via `glab`
- **GitLab canonical** — GitLab is canonical, local files are absent or secondary
- **Other** — record the workflow in plain prose

If a GitHub or GitLab remote exists, mention it as an available option, not the default.

**Section C — Coding guidelines.**

> Explainer: a `## Coding guidelines` section in the repo's agent instruction
> file sets ambient behavioral rules for coding sessions in this repo. Keep it
> if it helps, skip it if it feels like ceremony.

Check whether a `## Coding guidelines` section already exists. If it does, show it and ask whether to keep, replace, or merge. If it doesn't, offer the existing default template.

**Do not proactively ask about context docs.** If `docs/CONTEXT.md`, `docs/CONTEXT-MAP.md`, or `docs/adr/` already exist, preserve them and mention them in the findings. Otherwise, treat them as optional follow-on docs that other skills create lazily when needed.

### 3. Confirm and edit

Show the user a draft of:

- The `## Agent skills` block to add to the repo's agent instruction file
- The `## Coding guidelines` section, if applicable
- `docs/agents/issue-tracker.md`
- `docs/agents/triage-labels.md` only if an external tracker adapter is configured
- `docs/agents/domain.md` only if the repo already has context docs or the user explicitly wants the reminder

Let them edit before writing.

### 4. Write

**Pick the file to edit:**

- If an agent instruction file exists, edit it.
- Else create `AGENTS.md`.

Never create a second agent instruction file when an equivalent one already
exists.

If an `## Agent skills` block already exists in the chosen file, update it in place rather than appending a duplicate. Same for `## Coding guidelines`.

Default `## Agent skills` block:

```markdown
## Agent skills

### Planning workflow

Start with `to-prd`, break the PRD into issues with `to-issues`, then implement one issue at a time with `tdd`. The canonical store and any mirror rules are defined in `docs/agents/issue-tracker.md`.

### Wayfinding

For an effort too big and foggy for one session, chart a map of decision tickets with `wayfinder` and resolve them one per session. Tracker mechanics live in the "Wayfinding operations" section of `docs/agents/issue-tracker.md`.

### External tracker

If this repo uses an external tracker, label and adapter rules live in `docs/agents/triage-labels.md`.

### Decision docs

ADRs live under `docs/adr/` and are created lazily for durable, non-obvious trade-offs.

### Optional context docs

If the repo uses glossary/context docs, they live under `docs/CONTEXT.md` or `docs/CONTEXT-MAP.md`. See `docs/agents/domain.md`.
```

Then write the companion docs using the seed templates in this skill folder:

- [issue-tracker-local.md](./issue-tracker-local.md) — local markdown source of truth
- [issue-tracker-github.md](./issue-tracker-github.md) — GitHub mirror workflow
- [issue-tracker-gitlab.md](./issue-tracker-gitlab.md) — GitLab mirror workflow
- [triage-labels.md](./triage-labels.md) — optional external label mapping
- [domain.md](./domain.md) — optional context doc conventions

For every repo, `docs/agents/issue-tracker.md` should be written with an explicit frontmatter contract describing the canonical store. `docs/agents/triage-labels.md` is optional and should only be written if an external tracker adapter is configured or the repo already has one. `docs/agents/domain.md` is optional and should only be written if the repo already has context docs or the user asks for it.

For "other" issue trackers, write `docs/agents/issue-tracker.md` from scratch using the user's description.

### 4a. Check the written docs are tracked

Run `git check-ignore -v` against every file you just wrote. Repos commonly
gitignore `docs/agents/`, `docs/CONTEXT.md`, and `docs/issues/` as "agent
scratch", which silently defeats the setup: an ignored file is untracked, so it
does not exist in a fresh clone or in any new `git worktree`, and agents working
there start with no tracker contract and no glossary.

Split the decision by what the file is:

- **Contracts and vocabulary must be tracked** — `docs/agents/*.md` and
  `docs/CONTEXT.md` are repo policy, not scratch. If they are ignored, tell the
  user and offer to un-ignore them.
- **Planning artifacts may stay ignored** — `docs/issues/` is high-churn and
  only needs tracking when local markdown is the canonical store. If an external
  tracker is canonical, leaving it ignored is correct.

Never work around an ignore rule with `git add -f`; fix `.gitignore` instead, so
the next worktree inherits the setup.

### 5. Done

Tell the user the setup is complete and which skills now rely on `docs/agents/issue-tracker.md`. Mention they can edit `docs/agents/*.md` directly later. Re-running this skill should only be necessary if they want to change the canonical store, local issue layout, or external tracker adapter.
