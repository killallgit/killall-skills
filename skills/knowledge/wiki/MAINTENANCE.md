# Maintenance

## Structural lint

Run `scripts/wiki-check.py`. Repair deterministic defects such as malformed
JSONL, broken generated indexes, and unambiguous link renames. Queue content
decisions for review.

Inspect:

- duplicate IDs and aliases;
- missing or unreachable sources;
- invalid temporal intervals;
- unknown types and predicates;
- contradictions and disputed claims;
- orphan or oversized pages;
- stale high-importance claims;
- missing cross-project relationships;
- voice or citation drift.

## Evaluation

Maintain real questions in `evals/questions.yaml`. Cover entity lookup,
multi-page synthesis, multi-hop relations, historical truth, knowledge updates,
and abstention. Evaluate evidence retrieval separately from final synthesis.
Ontology or retrieval changes must not improve one question by regressing
unrelated questions.

## Ontology

The ontology is a contract, not a tag dump. Keep stable entity/page types,
predicates, inverses, aliases, cardinality, and temporal behavior in
`ontology/schema.yaml`.

Unknown vocabulary enters `ontology/candidates.yaml` with examples and source
IDs. Promote only after repeated use or explicit approval. Record versioned
migrations for renamed types or predicates; update claims, pages, and aliases
atomically.

JSON-LD, RDF, SHACL, GraphRAG, Graphiti, and graph databases are optional
projections. Rebuild them from canonical vault data and never accept projection
state as unsupported truth.

## Journal and session context

Write `journal/YYYY-MM-DD.md` with durable learnings, changed artifacts, open
questions, and queued reviews. Keep `KNOWLEDGE.md` bounded to current focus,
recent material, stale reviews, and unresolved contradictions. It is session
context, not an archive.

## Scale discipline

Use bounded scans and delegate large reading jobs only when permitted. Never
load all raw sources or the full claims ledger into the main context. Prefer
stable IDs, hashes, targeted JSONL scans, focused page reads, and rebuildable
indexes.
