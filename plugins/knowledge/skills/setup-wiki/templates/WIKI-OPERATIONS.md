# Wiki Operations

## Observe

Read `wiki.json`. Work only inside included project roots and honor every
exclusion. Identify changed eligible sources by stable ID and content hash.

## Ingest

1. Read one source completely.
2. Record its stable ID, hash, origin, acquisition time, and sensitivity in
   `raw/manifest.jsonl`.
3. Extract candidate entities, aliases, claims, events, and typed relations
   with exact source anchors.
4. Resolve identities against existing pages and aliases.
5. Reconcile duplicate, contradictory, and temporal claims.
6. Propose ADD, UPDATE, DELETE, or NOOP decisions for affected pages.
7. Queue knowledge-bearing changes for review.
8. Compile approved changes, validate, evaluate, and append `runs/log.jsonl`.

## Query

Search `wiki/` and the claim graph, follow relevant links, then open supporting
sources for load-bearing claims. Answer with citations. State when evidence is
missing. Queue reusable synthesis instead of leaving it only in chat.

## Lint

Run `python3 scripts/wiki-check.py .`. Review stale claims, contradictions,
orphans, aliases, ontology candidates, and missing evidence. Never resolve
knowledge conflicts through mechanical rewrites.

## Evaluate

Run the representative questions in `evals/questions.yaml`. Check evidence
coverage, multi-page reasoning, historical truth, updates, and abstention.

## Ontology

Keep `ontology/schema.yaml` small. Put unknown types and predicates in
`ontology/candidates.yaml`. Promote repeated or explicitly approved vocabulary
with a versioned migration for renames.

## Journal

Write `journal/YYYY-MM-DD.md` with durable learnings, changed pages, open
questions, and queued reviews. Keep `KNOWLEDGE.md` bounded and current.
