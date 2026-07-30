# Generic Wiki Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `setup-wiki` and `wiki` skills that create and operate a portable cross-project Markdown wiki with a typed claim graph, lightweight ontology, validators, and optional merged lifecycle hooks.

**Architecture:** `setup-wiki` conducts the user interview and invokes a Python standard-library scaffold. Static templates remain inspectable under the skill, while copied vault scripts provide validation and lifecycle integration after installation. `wiki` discovers the vault through `.wiki.json` project pointers and runs bounded ingest, query, reconciliation, lint, evaluation, and ontology workflows against Markdown and JSONL canonical data.

**Tech Stack:** Agent Skills Markdown, Python 3 standard library, POSIX shell only where host launchers require it, `unittest`, JSON/JSONL, YAML templates.

## Global Constraints

- The vault always spans projects and defaults to `<projects-root>/<name>-wiki`.
- Markdown, sources, claims, and ontology files are canonical; indexes and graph services are rebuildable projections.
- Raw sources are immutable after ingest.
- Knowledge-bearing changes enter review; deterministic metadata and index maintenance may apply automatically.
- Hook installation is optional, confirmed, backed up, merged, and reversible.
- No host-specific package metadata belongs under `payload/skills/`.
- Do not require Obsidian, qmd, embeddings, RDF, or a graph database.
- Comments explain only constraints or non-obvious behavior.

---

### Task 1: Deterministic Cross-Project Vault Scaffold

**Files:**
- Create: `tests/test_wiki_scaffold.py`
- Create: `payload/skills/setup-wiki/scripts/wiki_setup.py`
- Create: `payload/skills/setup-wiki/scripts/setup-wiki.py`
- Create: `payload/skills/setup-wiki/templates/AGENTS.md`
- Create: `payload/skills/setup-wiki/templates/KNOWLEDGE.md`
- Create: `payload/skills/setup-wiki/templates/WIKI-OPERATIONS.md`
- Create: `payload/skills/setup-wiki/templates/wiki-index.md`
- Create: `payload/skills/setup-wiki/templates/wiki-overview.md`
- Create: `payload/skills/setup-wiki/templates/ontology-schema.yaml`
- Create: `payload/skills/setup-wiki/templates/ontology-candidates.yaml`
- Create: `payload/skills/setup-wiki/templates/ontology-aliases.yaml`
- Create: `payload/skills/setup-wiki/templates/eval-questions.yaml`

**Interfaces:**
- Produces: `scaffold_vault(vault: Path, name: str, purpose: str, projects: list[Path], excludes: list[str]) -> ScaffoldResult`
- Produces: `ScaffoldResult(created: tuple[Path, ...], preserved: tuple[Path, ...], pointers: tuple[Path, ...])`
- Produces CLI: `setup-wiki.py --vault PATH --name NAME --purpose TEXT --project PATH... --exclude GLOB...`

- [ ] **Step 1: Write failing scaffold tests**

Create real temporary Git-like project directories and assert:

```python
result = scaffold_vault(
    vault=projects_root / "platform-wiki",
    name="platform",
    purpose="Explain how the platform projects fit together.",
    projects=[projects_root / "api", projects_root / "web"],
    excludes=["**/.env", "**/dist/**"],
)

self.assertEqual(json.loads((vault / "wiki.json").read_text())["projects"], [
    str((projects_root / "api").resolve()),
    str((projects_root / "web").resolve()),
])
self.assertEqual(json.loads((projects_root / "api" / ".wiki.json").read_text())["vault"], str(vault.resolve()))
self.assertTrue((vault / "ontology" / "schema.yaml").is_file())
self.assertTrue((vault / "queues" / "contradictions").is_dir())
```

Add a second test proving reruns preserve a user-edited `wiki/overview.md` and report it in `preserved`.

- [ ] **Step 2: Run the scaffold tests and verify RED**

Run: `python3 -m unittest tests.test_wiki_scaffold -v`

Expected: import failure for missing `payload.skills.setup-wiki.scripts.wiki_setup`.

- [ ] **Step 3: Implement the minimal scaffold**

Implement:

```python
@dataclass(frozen=True)
class ScaffoldResult:
    created: tuple[Path, ...]
    preserved: tuple[Path, ...]
    pointers: tuple[Path, ...]

def scaffold_vault(vault, name, purpose, projects, excludes):
    resolved_projects = tuple(Path(project).resolve() for project in projects)
    if not resolved_projects:
        raise ValueError("at least one project is required")
    if vault.exists() and not vault.is_dir():
        raise ValueError(f"vault path is not a directory: {vault}")
    # Create only missing directories and files; never rewrite existing content.
```

Render `{{WIKI_NAME}}`, `{{PURPOSE}}`, and generated UTC dates in templates. Write `wiki.json` atomically with resolved projects and exclusions. Write `.wiki.json` pointers atomically only when absent or already point to the same vault; reject conflicting pointers.

- [ ] **Step 4: Run scaffold tests and verify GREEN**

Run: `python3 -m unittest tests.test_wiki_scaffold -v`

Expected: both scaffold tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_wiki_scaffold.py payload/skills/setup-wiki
git commit -m "feat(wiki): add cross-project vault scaffold"
```

### Task 2: Vault Integrity Validator

**Files:**
- Create: `tests/test_wiki_validator.py`
- Create: `payload/skills/setup-wiki/scripts/wiki_check.py`
- Modify: `payload/skills/setup-wiki/scripts/wiki_setup.py`
- Modify: `payload/skills/setup-wiki/templates/AGENTS.md`
- Modify: `payload/skills/setup-wiki/templates/WIKI-OPERATIONS.md`

**Interfaces:**
- Consumes: generated `wiki.json`, `ontology/schema.yaml`, Markdown pages, and `claims/*.jsonl`
- Produces: `check_vault(vault: Path) -> CheckResult`
- Produces: `CheckResult(errors: tuple[str, ...], warnings: tuple[str, ...])`
- Produces CLI: copied vault command `scripts/wiki-check.py [VAULT]`

- [ ] **Step 1: Write failing validator tests**

Scaffold a vault, add a source page and claims ledger, then assert:

```python
result = check_vault(vault)
self.assertEqual(result.errors, ())
```

Add mutations that must fail independently:

```python
self.assertIn("duplicate claim id: claim-1", result.errors)
self.assertIn("claim claim-2 references missing source: source-missing", result.errors)
self.assertIn("claim claim-3 has valid_to before valid_from", result.errors)
self.assertIn("wiki/concepts/broken.md links to missing page: absent-page", result.errors)
```

- [ ] **Step 2: Run validator tests and verify RED**

Run: `python3 -m unittest tests.test_wiki_validator -v`

Expected: import failure for missing `wiki_check`.

- [ ] **Step 3: Implement validation**

Parse JSON and JSONL with line-numbered diagnostics. Validate:

- required scaffold paths;
- unique source, page, entity, and claim IDs;
- allowed claim states;
- source references;
- ISO date ordering for `valid_from` and `valid_to`;
- ontology predicate membership;
- `[[wikilink]]` targets;
- project pointer consistency.

Return warnings for orphan pages and empty evaluation questions. Never modify content during validation. Copy the executable validator into generated vaults during scaffold.

- [ ] **Step 4: Run validator and scaffold tests**

Run: `python3 -m unittest tests.test_wiki_validator tests.test_wiki_scaffold -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_wiki_validator.py payload/skills/setup-wiki
git commit -m "feat(wiki): validate graph integrity and provenance"
```

### Task 3: Portable Lifecycle Hooks and Safe Installer

**Files:**
- Create: `tests/test_wiki_hooks.py`
- Create: `payload/skills/setup-wiki/scripts/install-wiki-hooks.py`
- Create: `payload/skills/setup-wiki/templates/hooks/wiki-session-start.py`
- Create: `payload/skills/setup-wiki/templates/hooks/wiki-session-end.py`
- Modify: `payload/skills/setup-wiki/scripts/wiki_setup.py`
- Modify: `payload/skills/setup-wiki/templates/WIKI-OPERATIONS.md`

**Interfaces:**
- Produces: `merge_hooks(config: dict, host: str, vault: Path) -> dict`
- Produces CLI: `install-wiki-hooks.py --host claude|codex --vault PATH --config PATH [--remove]`
- Produces hook contract: JSON on stdin; bounded context on SessionStart; metadata-only review candidate on SessionEnd.

- [ ] **Step 1: Write failing installer and hook behavior tests**

Assert real JSON transformations:

```python
merged = merge_hooks(existing, "codex", vault)
self.assertEqual(len(merged["hooks"]["PreToolUse"]), 1)
self.assertEqual(len(merged["hooks"]["SessionStart"]), 1)
self.assertEqual(len(merged["hooks"]["SessionEnd"]), 1)
self.assertEqual(merge_hooks(merged, "codex", vault), merged)
```

Run generated hooks as subprocesses. Assert SessionStart emits bounded `KNOWLEDGE.md` context only for a scoped project. Assert SessionEnd creates one queue item containing `cwd`, `session_id`, UTC timestamp, and dirty-file count without transcript text or filenames. Assert clean or out-of-scope sessions create nothing.

Test malformed JSON leaves the config byte-for-byte unchanged. Test `--remove` deletes only handlers pointing to this vault. Test writes create a timestamped backup.

- [ ] **Step 2: Run hook tests and verify RED**

Run: `python3 -m unittest tests.test_wiki_hooks -v`

Expected: missing installer and hook templates.

- [ ] **Step 3: Implement cross-host hook integration**

Use current host contracts:

- Claude user config: `~/.claude/settings.json`; `SessionStart` and `SessionEnd`.
- Codex user config: `~/.codex/hooks.json`; `SessionStart` and `SessionEnd`.
- Both commands invoke absolute vault-local scripts.
- Do not edit Codex `config.toml`; hooks are enabled by default and `codex_hooks` is deprecated.
- Preserve unrelated event groups and handlers.
- Back up before every changed write.

SessionStart reads at most 8 KiB from `KNOWLEDGE.md` and emits plain text. SessionEnd never reads transcripts or assistant messages. It checks whether `cwd` is inside a configured project and whether that project has relevant Git changes before atomically writing a review candidate.

- [ ] **Step 4: Run hook tests and verify GREEN**

Run: `python3 -m unittest tests.test_wiki_hooks -v`

Expected: all hook tests pass without warnings.

- [ ] **Step 5: Commit**

```bash
git add tests/test_wiki_hooks.py payload/skills/setup-wiki
git commit -m "feat(wiki): add reversible lifecycle hook setup"
```

### Task 4: Setup and Runtime Skill Contracts

**Files:**
- Create: `payload/skills/setup-wiki/SKILL.md`
- Create: `payload/skills/setup-wiki/INTERVIEW.md`
- Create: `payload/skills/setup-wiki/HOOKS.md`
- Create: `payload/skills/wiki/SKILL.md`
- Create: `payload/skills/wiki/INGEST.md`
- Create: `payload/skills/wiki/QUERY.md`
- Create: `payload/skills/wiki/MAINTENANCE.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: scaffold and installer CLIs from Tasks 1–3.
- Produces trigger `/setup-wiki`: discover, interview one question at a time, summarize, confirm, scaffold, optionally install hooks, validate, report.
- Produces trigger `/wiki`: discover `.wiki.json`, refresh safely, select one bounded workflow, validate/persist, report.

- [ ] **Step 1: Write contract pressure tests**

Extend `tests/test_wiki_scaffold.py` with an integration test that invokes `setup-wiki.py`, loads the generated contract, and verifies a generic agent can discover:

- included projects and exclusions from `wiki.json`;
- canonical raw/wiki/claims/ontology boundaries;
- ingest, query, lint, ontology, journal, and evaluation entry points;
- the queue-first knowledge boundary;
- validator and hook installation commands.

The test asserts generated behavior and files, not exact prose in skill documents.

- [ ] **Step 2: Run the integration test and verify RED**

Run: `python3 -m unittest tests.test_wiki_scaffold.WikiScaffoldTests.test_generated_contract_exposes_runtime_workflows -v`

Expected: failure because runtime contract sections are absent.

- [ ] **Step 3: Write focused skill documents**

Keep each `SKILL.md` under 100 lines. `setup-wiki` links directly to:

- `INTERVIEW.md` for discovery, the one-question-at-a-time interview, confirmation, and adoption rules;
- `HOOKS.md` for official host locations, backup/merge behavior, trust/restart notes, removal, and verification.

`wiki` links directly to:

- `INGEST.md` for immutable sources, stable hashes, ADD/UPDATE/DELETE/NOOP decisions, identity resolution, temporal reconciliation, and review queues;
- `QUERY.md` for bounded retrieval, citations, graph traversal, abstention, and filing valuable synthesis;
- `MAINTENANCE.md` for validation, lint, evaluation questions, ontology candidates, journaling, and optional projections.

Update the README current-state description to include cross-project wiki setup and maintenance.

- [ ] **Step 4: Run all tests and skill validation**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 payload/skills/setup-wiki/scripts/setup-wiki.py --help
python3 payload/skills/setup-wiki/scripts/install-wiki-hooks.py --help
```

Expected: all tests pass and both CLIs exit 0.

- [ ] **Step 5: Commit**

```bash
git add README.md tests payload/skills/setup-wiki payload/skills/wiki
git commit -m "feat(wiki): add setup and runtime skills"
```

### Task 5: Full Verification and Distribution Review

**Files:**
- Modify only if verification exposes a defect.

**Interfaces:**
- Consumes all prior tasks.
- Produces a clean, installable skill pack.

- [ ] **Step 1: Run fresh full verification**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q payload/skills/setup-wiki/scripts payload/skills/setup-wiki/templates/hooks
git diff --check main...HEAD
```

Expected: zero failures and exit 0.

- [ ] **Step 2: Validate every skill and relative reference**

Run the repository Ruby validator over `payload/skills/*/SKILL.md`:

- frontmatter `name` equals directory name;
- description exists;
- every relative Markdown link exists;
- intended scripts are executable;
- plugin manifests parse as JSON.

Expected: 30 skills validate.

- [ ] **Step 3: Exercise a temporary end-to-end vault**

Create two temporary project directories, scaffold one shared vault, install hooks into temporary Claude and Codex configs, run SessionStart and SessionEnd payloads, validate the resulting vault, uninstall hooks, and confirm unrelated config survives.

Expected: all commands exit 0; only the scoped vault and temporary configs change.

- [ ] **Step 4: Review requirements against the approved design**

Confirm every design section maps to implementation: placement, scope, structure, claims, ontology, ingest/query/lint/evaluation, hybrid hooks, failure handling, and optional-tool degradation.

- [ ] **Step 5: Commit verification fixes if needed**

```bash
git add README.md tests payload/skills/setup-wiki payload/skills/wiki
git commit -m "fix(wiki): address verification findings"
```
