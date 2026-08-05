# Domain Bundle Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the monolithic plugin payload with five independently installable domain plugins while keeping 23 skills individually discoverable.

**Architecture:** Each directory under `plugins/` is a complete Claude Code and Codex plugin and owns its skills and optional agents. Root marketplace files expose the five domains; `install.sh` selects validated domain names, while the `skills` CLI discovers individual nested skills.

**Tech Stack:** Bash, JSON manifests, Python `unittest`, Markdown Agent Skills.

## Global Constraints

- Domain names are exactly `planning`, `engineering`, `architecture`, `knowledge`, and `experimental`.
- There is no umbrella plugin and no implicit install-all behavior.
- Plugin directories are dependency-closed and contain the canonical skill files.
- Existing user configuration is never overwritten by the installer.
- Production behavior changes follow red-green-refactor.

---

### Task 1: Define the domain manifest and inventory contract

**Files:**
- Create: `tests/test_plugins.py`
- Create: `plugins/<domain>/.claude-plugin/plugin.json`
- Create: `plugins/<domain>/.codex-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `.agents/plugins/marketplace.json`

**Interfaces:**
- Consumes: the approved five-domain inventory in the design document.
- Produces: five marketplace entries and ten matching plugin manifests.

- [ ] **Step 1: Write failing manifest and inventory tests**

Add tests that load both marketplaces, require the exact five names, verify
their source directories, compare both host inventories, check manifest names,
and assert the expected skill names under each plugin.

- [ ] **Step 2: Run the new tests and verify RED**

Run: `python3 -m unittest tests.test_plugins -v`

Expected: failure because `plugins/` and the five marketplace entries do not
exist.

- [ ] **Step 3: Add the minimal manifests and domain directories**

Create both host manifests for each domain at version `0.5.0`. Point Codex's
`skills` field at `./skills/`. Replace the two root marketplace plugin arrays
with the five local domain sources.

- [ ] **Step 4: Run the manifest portion and verify GREEN**

Run: `python3 -m unittest tests.test_plugins.PluginManifestTests -v`

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin .agents/plugins plugins tests/test_plugins.py
git commit -m "feat: define domain plugin manifests"
```

### Task 2: Implement selective installer behavior

**Files:**
- Modify: `tests/test_install.py`
- Modify: `install.sh`

**Interfaces:**
- Consumes: exact domain names from Task 1.
- Produces: `./install.sh [--remove] [--all|<domain>...]` and `--list`.

- [ ] **Step 1: Replace monolith tests with selective-install tests**

Test no-argument usage, one domain, multiple domains, `--all`, `--remove`,
`--list`, and invalid domains. Assert exact Claude and Codex plugin identifiers.

- [ ] **Step 2: Run installer tests and verify RED**

Run: `python3 -m unittest tests.test_install -v`

Expected: failures because the current installer accepts no domain arguments
and always installs `killall-skills`.

- [ ] **Step 3: Implement the minimal selector parser**

Use one Bash array containing the five domains. Validate all input before
calling hosts. Add/update the marketplace once for installations, then refresh
only the selected plugins. Removal must not add or update marketplaces.

- [ ] **Step 4: Run installer tests and verify GREEN**

Run: `python3 -m unittest tests.test_install -v`

- [ ] **Step 5: Commit**

```bash
git add install.sh tests/test_install.py
git commit -m "feat: install selected domain plugins"
```

### Task 3: Move and simplify Planning, Engineering, and Architecture

**Files:**
- Move: surviving `payload/skills/` directories into the owning `plugins/<domain>/skills/` directory.
- Move: `payload/agents/project-planner.md` to `plugins/planning/agents/`.
- Move: `payload/agents/git-janitor-investigator.md` to `plugins/engineering/agents/`.
- Create: `plugins/experimental/skills/create-extension/SKILL.md`.
- Remove: retired skill directories listed in the design.
- Modify: moved skills that refer to retired or cross-domain skills.

**Interfaces:**
- Consumes: the exact 23-skill inventory asserted by `tests/test_plugins.py`.
- Produces: dependency-closed domain skill directories with no stale invocations.

- [ ] **Step 1: Extend inventory tests with forbidden paths and references**

Assert retired directories are absent, `setup-planning` replaces
`setup-skills`, and active skill text does not invoke removed skill names.

- [ ] **Step 2: Run inventory tests and verify RED**

Run: `python3 -m unittest tests.test_plugins.PluginInventoryTests -v`

- [ ] **Step 3: Move the canonical skill directories**

Use filesystem moves for retained directories. Rename `setup-skills` to
`setup-planning`. Move the two Claude agents to their owning plugins.

- [ ] **Step 4: Fold retired behavior into survivors**

Make planning clarification self-contained, add the documentation interview to
`domain-modeling`, merge safe worktree cleanup into `git-janitor`, and create
`create-extension` from the three authoring workflows.

- [ ] **Step 5: Remove retired directories and stale references**

Remove `grilling`, `grill-me`, `grill-with-docs`, `worktree-cleanup`,
`setup-pre-commit`, `zoom-out`, `create-skill`, `create-rule`, `create-hook`, and
`init-project`. Update `setup-skills` invocations to `setup-planning`.

- [ ] **Step 6: Run inventory tests and verify GREEN**

Run: `python3 -m unittest tests.test_plugins -v`

- [ ] **Step 7: Commit**

```bash
git add plugins payload tests/test_plugins.py
git commit -m "refactor: organize skills by domain"
```

### Task 4: Relocate knowledge tests and preserve runtime behavior

**Files:**
- Modify: `tests/test_wiki_hooks.py`
- Modify: `tests/test_wiki_validator.py`
- Modify: `tests/test_proofcast.py`

**Interfaces:**
- Consumes: knowledge and experimental plugin paths from Task 3.
- Produces: existing behavioral coverage against canonical relocated paths.

- [ ] **Step 1: Update test path constants only after the move**

Point wiki tests at `plugins/knowledge/skills/setup-wiki/` and the recording
test at `plugins/experimental/skills/record/SKILL.md`.

- [ ] **Step 2: Run the affected tests**

Run: `python3 -m unittest tests.test_wiki_hooks tests.test_wiki_scaffold tests.test_wiki_validator tests.test_proofcast -v`

Expected: all pass against the relocated files.

- [ ] **Step 3: Commit**

```bash
git add tests
git commit -m "test: follow relocated domain skills"
```

### Task 5: Publish the current installation contract

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `hooks/README.md`
- Modify: `hooks/voice-readback/README.md`
- Modify: `CHANGELOG.md`
- Remove: `payload/`

**Interfaces:**
- Consumes: installer commands and final paths from Tasks 1-4.
- Produces: current-state documentation for bundles, individual skills, and local development.

- [ ] **Step 1: Add documentation assertions**

Extend `tests/test_plugins.py` to require all five bundles in the README and
reject monolithic install commands and `payload/` current-state references.

- [ ] **Step 2: Run documentation tests and verify RED**

Run: `python3 -m unittest tests.test_plugins.PluginDocumentationTests -v`

- [ ] **Step 3: Update current-state documentation and changelog**

Document selective bundle installs, `--all`, removal, and the one-skill `npx`
command. Update authoring and voice-hook references for the new structure. Add
the `0.5.0` changelog entry.

- [ ] **Step 4: Run documentation tests and verify GREEN**

Run: `python3 -m unittest tests.test_plugins.PluginDocumentationTests -v`

- [ ] **Step 5: Commit**

```bash
git add README.md AGENTS.md hooks CHANGELOG.md tests/test_plugins.py payload
git commit -m "docs: publish domain bundle installation"
```

### Task 6: Validate public discovery and release state

**Files:**
- Modify only if validation exposes a defect.

**Interfaces:**
- Consumes: complete repository state.
- Produces: evidence that tests, manifests, scripts, and skill discovery work.

- [ ] **Step 1: Run the full unit suite**

Run: `python3 -m unittest discover -s tests -v`

- [ ] **Step 2: Validate shell and Python files**

Run: `bash -n install.sh scripts/proofcast`

Run: `python3 -m compileall -q plugins/knowledge/skills/setup-wiki/scripts plugins/knowledge/skills/setup-wiki/templates/hooks`

- [ ] **Step 3: Validate whitespace and manifests**

Run: `git diff --check`

Run: `claude plugin validate .`

- [ ] **Step 4: Verify individual skill discovery locally**

Run: `npx skills@latest add . --list`

Expected: exactly 23 available skills grouped under the five plugin sources.

- [ ] **Step 5: Review the requirements line by line and commit fixes**

If any validation-required fixes were made:

```bash
git add -A
git commit -m "fix: complete domain bundle validation"
```
