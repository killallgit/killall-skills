# Domain bundle distribution design

## Goal

Distribute the repository as five independently installable Claude Code and
Codex plugins while preserving one-skill-at-a-time installation through the
cross-agent `skills` CLI.

## Domains

### Planning

- `project-planner`
- `setup-planning`
- `to-prd`
- `to-issues`
- `triage`
- `wayfinder`

`setup-planning` replaces `setup-skills`. The generic grilling behavior is
embedded into the planning workflows that need it. `grilling` and `grill-me`
are not separate installable skills.

### Engineering

- `tdd`
- `diagnose`
- `code-review`
- `review-library-usage`
- `resolving-merge-conflicts`
- `git-janitor`
- `wait-for-action`

`git-janitor` owns worktree cleanup. `worktree-cleanup` is not a separate
skill. The stack-specific `setup-pre-commit` recipe is not distributed.

### Architecture

- `domain-modeling`
- `codebase-design`
- `improve-codebase-architecture`

`domain-modeling` owns the one-question-at-a-time documentation workflow from
`grill-with-docs`. `zoom-out` is not distributed as a standalone skill.

### Knowledge

- `research`
- `setup-wiki`
- `wiki`
- `handoff`

Wiki setup remains separate from wiki operation because setup provisions vaults,
project pointers, policies, and optional hooks, while operation performs ingest,
query, maintenance, validation, journaling, and synchronization.

### Experimental

- `prototype`
- `record`
- `create-extension`

`create-extension` replaces the separate `create-skill`, `create-rule`, and
`create-hook` authoring workflows. `init-project` is replaced by the repository
installer and marketplace documentation.

## Repository structure

Each domain is a complete plugin root:

```text
plugins/<domain>/
├── .claude-plugin/plugin.json
├── .codex-plugin/plugin.json
├── skills/
└── agents/                    # only when the domain needs Claude agents
```

The Claude and Codex marketplace files list the same five domain names and map
each name to `plugins/<domain>`. Skill content has one canonical location under
its owning plugin. No generated copies or cross-plugin symlinks are used.

Every plugin is dependency-closed. References to skills in another plugin must
be optional and include an inline fallback. References to removed skills are
folded into the surviving workflow that needs the behavior.

## Installation contract

The repository installer accepts one or more domain names:

```bash
./install.sh planning
./install.sh planning engineering
./install.sh --remove knowledge
./install.sh --all
./install.sh --list
```

With no domains and without `--all`, it prints usage and performs no install.
The installer validates every requested domain before invoking either host.
`--all` means all five domain plugins; there is no umbrella plugin.

Individual skills use the host-neutral installer:

```bash
npx skills@latest add killallgit/killall-skills \
  --skill research \
  --agent claude-code \
  --agent codex \
  --global \
  --yes
```

## Validation

Automated tests enforce:

- the exact five marketplace entries and matching dual manifests;
- the exact 23-skill domain inventory;
- absence of removed skill directories and stale references;
- selective, multiple-domain, removal, listing, invalid-input, and `--all`
  installer behavior;
- existing wiki, hook, proofcast, and validator behavior after relocation.

The release updates current-state documentation and records the distribution
change in the changelog.
