# Generic Cross-Project Wiki Design

Date: 2026-07-30

## Goal

Add two portable skills:

- `setup-wiki` creates or adopts a shared, cross-project knowledge vault and
  configures its integrations.
- `wiki` operates that vault through ingest, query, reconciliation, lint,
  journaling, ontology maintenance, and graph workflows.

The vault must remain useful as plain Markdown without Obsidian, embeddings, an
MCP server, or a graph database.

## Design principles

The system follows the three-layer LLM wiki pattern:

1. Immutable source material remains the evidence layer.
2. Agent-maintained Markdown pages form a compiled, interlinked knowledge
   layer.
3. A versioned contract governs page structure, citations, ingest, query, and
   maintenance.

It extends that pattern with:

- stable source, entity, claim, and operation IDs;
- claim-level provenance and temporal validity;
- a small, versioned ontology;
- candidate and contradiction review queues;
- representative evaluation questions;
- optional, rebuildable search and graph projections.

Markdown and compact ledgers are canonical. Generated indexes, embeddings, and
external graph databases are disposable projections.

## Vault placement and scope

A wiki always spans projects. The preferred location is:

```text
<projects-root>/<name>-wiki/
```

When the current repository is already directly below the projects root, this
is equivalent to `../<name>-wiki`.

Setup discovers likely project roots from the current path and nearby Git
repositories, then asks the user to confirm:

- the vault name and location;
- the purpose and representative questions;
- included project roots;
- excluded and sensitive paths;
- source types and external systems;
- audience and write permissions;
- freshness expectations;
- initial entity, page, and relationship types;
- retrieval tools;
- Git and review policy;
- detected hosts eligible for hooks.

The skill presents a complete setup summary before creating files or changing
configuration outside the vault.

Each participating project receives a small pointer to the vault. The pointer
records the vault path, scope, and exclusions without duplicating the wiki
contract.

## Generated structure

```text
<name>-wiki/
├── AGENTS.md
├── KNOWLEDGE.md
├── WIKI-OPERATIONS.md
├── raw/
├── wiki/
│   ├── index.md
│   ├── overview.md
│   ├── entities/
│   ├── concepts/
│   ├── decisions/
│   ├── procedures/
│   └── sources/
├── claims/
├── ontology/
│   ├── schema.yaml
│   ├── candidates.yaml
│   └── aliases.yaml
├── queues/
│   ├── ingest/
│   ├── review/
│   └── contradictions/
├── indexes/
├── evals/
│   └── questions.yaml
├── journal/
└── runs/
    └── log.jsonl
```

`AGENTS.md` is the portable contract. `KNOWLEDGE.md` is the bounded session
entry point. `WIKI-OPERATIONS.md` is loaded only for operational workflows.

## Knowledge model

Sources have stable IDs, content hashes, acquisition timestamps, original
locations, and sensitivity labels.

Claims include:

- a stable ID and self-contained statement;
- source IDs and precise source anchors;
- lifecycle state: `candidate`, `verified`, `disputed`, or `superseded`;
- `observed_at`;
- optional `valid_from` and `valid_to`;
- optional subject, predicate, and object entity IDs;
- operational confidence based on source quality, directness, agreement, and
  human review.

Contradictions preserve both claims and create a review item. New current truth
closes or supersedes the prior claim instead of erasing it.

The initial ontology defines universal page types, entity types, claim fields,
and a small relationship vocabulary. Unknown types and predicates enter
`ontology/candidates.yaml`. Promotion requires repeated use or explicit human
approval. Ontology versions and migrations handle renamed types and predicates.

Formal RDF, JSON-LD, SHACL, GraphRAG, Graphiti, or another graph backend may be
added as projections. They are not required by the core workflow.

## Runtime workflows

The main maintenance loop is:

```text
observe → extract → resolve → reconcile → compile
        → validate → evaluate → review → learn
```

### Ingest

Hash eligible sources, skip unchanged inputs, extract candidate entities and
claims with source anchors, resolve aliases and identities, reconcile temporal
or contradictory claims, then propose focused page patches. Re-ingesting an
unchanged source is a no-op.

### Query

Classify the question, retrieve through lexical search and graph links, open
the supporting pages and claims, and answer with citations. Valuable synthesis
may be proposed as a new page or claim set. Absence of evidence produces an
explicit abstention.

### Lint and evaluation

Check identifiers, links, source reachability, temporal intervals, ontology
constraints, duplicates, contradictions, stale claims, missing pages, and
orphans. Run representative questions from `evals/questions.yaml` to test
evidence coverage, multi-page synthesis, historical queries, updates, and
abstention.

### Ontology maintenance

Review aliases and candidate types or predicates. Low-confidence identity
merges, destructive changes, and ontology promotions require human approval.

### Journal

Record durable session outcomes, changed pages, open questions, and queued
reviews. Refresh the bounded session entry point without turning it into a
transcript.

## Hooks

Hooks are optional adapters around vault operations:

- session start surfaces bounded recent context, stale reviews, and unresolved
  contradictions;
- session end queues durable learning candidates when relevant activity
  occurred;
- eligible source changes enqueue ingest by stable ID and hash;
- pre-commit or manual checks validate structure and provenance;
- scheduled maintenance checks staleness, contradictions, ontology candidates,
  and evaluations.

The automation boundary is hybrid:

- deterministic metadata, link, and generated-index maintenance may apply
  automatically;
- new claims, contradictions, entity merges, destructive changes, and ontology
  changes enter review queues.

Hook registration is a separate, confirmed side effect. Installers detect the
host, back up configuration, merge existing hooks, and stop rather than
clobbering an incompatible registration. The vault operates normally without
hooks.

## Failure handling

- Existing non-empty targets are adopted only after inspection and approval.
- Dirty repositories are never reset or swept into wiki commits.
- Missing optional tools degrade to plain Markdown and lexical search.
- Unreachable projects or sources are reported and queued for review.
- Ambiguous entity matches remain candidates.
- Invalid temporal intervals or ontology violations block publication.
- Sensitive or excluded paths are never copied or indexed.
- Partial setup records completed actions and precise manual follow-up.

## Verification

Tests and fixtures cover:

- fresh scaffold and adoption of an existing vault;
- idempotent reruns;
- projects under shared and nonstandard roots;
- exclusions and sensitivity boundaries;
- unchanged and changed source ingestion;
- duplicate entities and contradictory claims;
- temporal supersession;
- ontology candidate promotion and migration;
- missing citations, files, links, and IDs;
- representative query retrieval and abstention;
- hook configuration merge, removal, and incompatible existing hooks;
- operation without Obsidian, qmd, embeddings, or a graph backend.

## Research basis

The supporting research and primary-source links are in
[Generic agent wiki: research and design implications](../research/2026-07-30-generic-agent-wiki.md).
