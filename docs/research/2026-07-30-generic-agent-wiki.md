# Generic agent wiki: research and design implications

Date: 2026-07-30

## Executive conclusion

`/setup-wiki` should create a Markdown-first, source-grounded knowledge system that works without a database, then offer search and graph backends as projections. The durable artifact should be understandable in a text editor and portable across agents; indexes, embeddings, and graph databases should always be rebuildable.

The most useful extension to the Karpathy pattern is a lightweight ontology plus a claim ledger:

- a small vocabulary of page types and typed relationships;
- stable IDs for sources, pages, entities, and claims;
- claim-level provenance, confidence, status, and temporal validity;
- candidate-review queues for uncertain extractions, contradictions, and ontology changes;
- feedback-driven maintenance and a small regression set of real questions.

Do not require RDF, Neo4j, embeddings, Obsidian, or a specific agent host. Generate a plain YAML ontology and Markdown conventions first; optionally export or validate with heavier tooling.

## What “the Karpathy method” means here

Karpathy's April 2026 [LLM Knowledge Bases post](https://x.com/karpathy/status/2039805659525644595) and [LLM Wiki idea file](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) describe a pattern rather than a product. It is intentionally an abstract pattern for an agent and user to instantiate together, not an official implementation specification.

The consistently reproduced core is:

1. **Raw sources** remain the evidence and are not silently rewritten.
2. **A compiled wiki** contains focused, interlinked Markdown pages synthesized by an LLM.
3. **A schema/instructions file** defines structure, citation, ingest, query, and maintenance behavior.
4. **Ingest** incorporates a source across every affected page, rather than writing one isolated summary.
5. **Query** navigates the compiled artifact and can preserve genuinely reusable synthesis.
6. **Lint/maintenance** repairs links, duplication, contradiction, staleness, and structural drift.
7. `index.md` is the navigation entry point and `log.md` is the chronological operating record.

The important shift is compilation: synthesis and cross-linking persist and compound instead of being recreated from raw chunks for every query. This is complementary to retrieval, not a reason to discard it.

## Findings from recent work

### 1. Graphs help, but provenance-bearing text remains essential

Microsoft's official [GraphRAG dataflow](https://microsoft.github.io/graphrag/index/default_dataflow/) extracts entities, relationships, time-bound claims, hierarchical communities, and community reports. It retains links from extracted knowledge to source text units specifically for provenance. Its [query engine](https://microsoft.github.io/graphrag/query/overview/) combines graph information with raw text for local questions and uses community summaries for corpus-wide questions.

Design implication: wikilinks and typed edges should improve navigation, but answers must still be able to reach supporting source passages. Community or hub summaries are useful cached views, not independent truth.

### 2. Evolving knowledge needs two clocks and non-destructive supersession

The 2025 [Zep temporal knowledge graph paper](https://arxiv.org/abs/2501.13956) and the official [Graphiti repository](https://github.com/getzep/graphiti) distinguish source episodes from derived facts, preserve historical relationships, and track temporal validity. Graphiti's useful portable concepts are:

- when a fact was true in the world (`valid_from`, `valid_to`);
- when the wiki learned or recorded it (`observed_at`, optionally `superseded_at`);
- old facts are closed or superseded, not erased;
- every derived fact traces to one or more source episodes.

Design implication: avoid a single ambiguous `date` or `updated` field. Temporal fields belong on claims and relationships, not just pages. Preserve disputed and superseded claims so historical questions remain answerable.

### 3. Memory quality improves through linking and evolution at write time

[A-MEM](https://arxiv.org/abs/2502.12110), published at NeurIPS 2025, applies Zettelkasten-like dynamic indexing and linking. New memories can update the contextual representation and attributes of related historical memories rather than merely appending another item.

Design implication: ingest should include a bounded neighborhood-refinement pass:

1. create or update the directly affected pages;
2. find nearby pages using titles, aliases, tags, links, and optional semantic search;
3. propose meaningful links and updates;
4. flag changes that alter established claims for review.

This should be bounded and idempotent. Re-ingesting the same source hash must not multiply pages or links.

### 4. Construction should learn from downstream questions

The very recent [WikiLoop preprint](https://arxiv.org/abs/2607.26604) couples a wiki Builder and Navigator: candidate edits are evaluated by whether they improve downstream evidence collection, with a guard against regressions on unrelated queries. This is promising but was published one day before this review and should be treated as an experimental signal, not settled evidence.

Design implication: keep a small `evals/questions.yaml` containing representative questions, expected source IDs or claims, and whether the correct behavior is to abstain. After structural or ontology changes, check that navigation still finds sufficient evidence before optimizing context cost.

### 5. Evaluation must include updates, time, and abstention

The ICLR 2025 [LongMemEval paper and benchmark](https://proceedings.iclr.cc/paper_files/paper/2025/file/d813d324dbf0598bbdc9c8e79740ed01-Paper-Conference.pdf) evaluates information extraction, multi-session reasoning, temporal reasoning, knowledge updates, and abstention. It also separates memory into indexing, retrieval, and reading, and reports benefits from fact-augmented keys and time-aware query expansion.

Design implication: wiki health is not link count. `/wiki-check` should test:

- source-to-claim extraction;
- multi-page synthesis;
- “as of” and historical questions;
- replacement of outdated current truth without loss of history;
- refusal when evidence is absent;
- retrieval quality separately from final-answer quality.

### 6. Treat memory as a governed lifecycle, not a pile of notes

[MemOS](https://arxiv.org/abs/2507.03724) models memory as a managed resource whose units carry provenance and versioning and can evolve over time. The implementation is broader than a project wiki, but the lifecycle framing is valuable.

Design implication: generated knowledge should have explicit states such as `candidate`, `reviewed`, `verified`, `disputed`, and `superseded`. Confidence must not be a free-floating model score: define it operationally from source quality, agreement, directness, and review status.

### 7. Ontologies are useful as contracts; full semantic-web machinery is optional

An ontology is more than a graph or a tag list. It defines the kinds of things that exist in the domain, allowed relationships, aliases, constraints, and sometimes inference rules.

The current [SHACL 1.2 Core draft](https://www.w3.org/TR/shacl12-core/) shows a practical model for graph constraints: node shapes, property shapes, cardinality, datatypes, and allowed values. [PROV-O](https://www.w3.org/TR/prov-o/) provides a mature minimal vocabulary for entities, activities, agents, derivation, revision, attribution, and primary sources. [OWL-Time](https://www.w3.org/TR/owl-time/) provides a vocabulary for instants, intervals, ordering, and duration.

Recent ontology-RAG work, including [OntoRAG](https://arxiv.org/abs/2506.00664) and a 2025 [comparison of ontology-learning approaches](https://arxiv.org/abs/2511.05991), reports benefits from ontology-guided knowledge graphs, but both are preprints and their pipelines are substantially heavier than a portable project wiki. They support offering ontology-backed retrieval, not making it the default.

Design implication: start with a small, domain-specific schema inspired by these standards:

```yaml
version: 1
entity_types: [person, organization, project, component, concept]
page_types: [overview, entity, concept, decision, procedure, source, question]
relation_types:
  - id: depends_on
    from: [project, component]
    to: [project, component]
    inverse: required_by
  - id: supersedes
    temporal: true
claim_fields:
  required: [id, statement, source_ids, status, observed_at]
  optional: [subject_id, predicate, object_id, confidence, valid_from, valid_to]
```

Keep this vocabulary small. Unknown types and predicates go to `ontology/candidates.yaml`; promotion into `ontology/schema.yaml` should require repeated use or explicit human approval. Version the ontology and provide migrations for renamed types and predicates.

## Recommended `/setup-wiki` interview

The setup skill should discover what it can from the current project, then ask only decisions it cannot safely infer:

1. **Purpose and success questions:** What should the wiki help answer or decide?
2. **Scope and audience:** One repository, several projects, a research topic, a personal vault, or a team?
3. **Vault location:** New directory, existing Obsidian vault, or wiki inside the project?
4. **Inputs:** Source directories, repositories, URLs, meeting notes, transcripts, issue trackers, or manual drop folder?
5. **Ownership:** Which files are immutable human sources, shared notes, or agent-maintained compiled pages?
6. **Sensitivity and boundaries:** Private material, excluded paths, retention, external-model restrictions, and who may write.
7. **Freshness:** Which claims change frequently, what “current” means, and review intervals.
8. **Domain model:** Seed types/relationships now, infer candidates from sources, or both.
9. **Tools:** Plain Markdown only; Obsidian; local lexical/semantic search; optional graph backend.
10. **Automation:** Which detected hosts may receive hooks, and whether hooks may only queue work or also apply reviewed edits.
11. **Version control:** Git tracking, generated-index policy, and whether commits remain user-controlled.

Show a setup summary and obtain confirmation before modifying config outside the vault or registering hooks.

## Recommended generated structure

```text
vault/
├── AGENTS.md                  # portable operating contract
├── KNOWLEDGE.md               # short entry point for any agent
├── raw/                       # source material; never rewritten by wiki jobs
├── wiki/
│   ├── index.md
│   ├── overview.md
│   ├── entities/
│   ├── concepts/
│   ├── decisions/
│   ├── procedures/
│   └── sources/
├── claims/                    # claim records or compact ledgers
├── ontology/
│   ├── schema.yaml
│   ├── candidates.yaml
│   └── aliases.yaml
├── queues/
│   ├── ingest/
│   ├── review/
│   └── contradictions/
├── indexes/                   # rebuildable generated artifacts
├── evals/
│   └── questions.yaml
└── runs/
    └── log.jsonl              # append-only machine-readable operations
```

`wiki/log.md` can be a human-readable projection of `runs/log.jsonl`. Raw sources should have a manifest with stable source IDs, content hashes, acquisition timestamps, original locations, and sensitivity labels. A source deletion or correction should trigger dependent-claim review, not silent cascading deletion.

## Hooks and automation

Hooks should be portable adapters around the same vault commands:

- **Session start:** surface `KNOWLEDGE.md`, recently changed pages, open contradictions, and stale review items.
- **Source/file change:** hash changed eligible inputs and enqueue ingest; do not ingest temporary files, secrets, build artifacts, or ignored paths.
- **Session end:** propose durable learnings from the session with source pointers; write candidates to a queue rather than asserting them as verified facts.
- **Scheduled maintenance:** run structural lint, stale-claim review, orphan detection, contradiction checks, ontology-candidate review, and eval questions.
- **Pre-commit/manual check:** validate frontmatter, IDs, links, source reachability, temporal intervals, and ontology constraints.

Default to “queue, do not silently publish.” Hook registration is host-specific and a side effect, so setup must detect existing configuration, back it up, merge rather than clobber, and ask before registration. The vault should remain fully usable when hooks are absent.

## Maintenance/refinement loop

1. **Observe:** detect new or changed sources by stable ID and hash.
2. **Extract:** produce candidate entities, claims, events, aliases, and relationships with exact source anchors.
3. **Reconcile:** match existing entities, surface contradictions, and determine valid-time changes.
4. **Compile:** patch focused wiki pages and indexes; do not regenerate the whole vault.
5. **Validate:** run structural, provenance, temporal, ontology, and link checks.
6. **Evaluate:** run representative questions; compare evidence coverage and abstention behavior.
7. **Review:** require human approval for low-confidence identity merges, destructive changes, sensitive material, and ontology promotion.
8. **Learn:** use query misses, excessive navigation, and repeated candidate types to improve aliases, summaries, links, and the ontology.

Every run should record inputs, hashes, generated patches, model/tool identity when available, validation results, and review disposition. This makes repair and rollback possible without making Git the only audit mechanism.

## Practical rollout

Implement in progressive levels:

1. **Core:** Markdown, immutable-source policy, stable IDs, citations, index, operation log, ingest/query/lint.
2. **Integrity:** claim ledger, hashes, lifecycle states, temporal validity, contradiction and stale-review queues.
3. **Ontology:** small YAML schema, aliases, typed edges, validation, candidate promotion.
4. **Retrieval:** lexical search first; optional semantic search and link traversal; generated indexes remain disposable.
5. **Scale:** optional GraphRAG/Graphiti-style projection, community summaries, and temporal graph queries.
6. **Learning:** eval questions and feedback-guided refinement.

This progression captures most of the value while preserving portability. The full-featured setup is the lifecycle and integrity model, not the number of services installed.
