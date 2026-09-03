# Ingest

## Observe

Accept explicit sources only. Check `wiki.json` scope and exclusions before
reading. Capture an immutable local snapshot under `raw/`; preserve its
original path or URI as optional origin metadata. Manifest entries require:

- stable source ID;
- path or URI;
- SHA-256 content hash;
- acquisition timestamp;
- sensitivity;
- optional project and source type.

An existing source ID with the same hash is NOOP. A changed hash creates a new
source episode; do not rewrite the prior evidence.

## Extract

Read one source completely. Briefly tell the user what it contributes. Extract
candidate entities, aliases, events, claims, and typed relations with exact
source anchors. Each claim is self-contained:

```json
{
  "id": "claim-...",
  "statement": "...",
  "source_ids": ["source-..."],
  "status": "candidate",
  "observed_at": "YYYY-MM-DD",
  "subject_id": "entity-...",
  "predicate": "depends_on",
  "object_id": "entity-...",
  "valid_from": "YYYY-MM-DD",
  "valid_to": null
}
```

Omit inapplicable optional fields. Confidence describes evidence quality,
directness, agreement, and review status; it is not an unexplained model score.

## Resolve and reconcile

Search titles, IDs, aliases, links, and nearby claims before creating an entity.
Distinguish the same entity from merely related entities. Ambiguous matches
enter `queues/review/`.

Use one of four page decisions with a rationale:

- ADD a distinct reusable entity, concept, decision, procedure, or synthesis.
- UPDATE attributes or claims on an existing page.
- DELETE only with explicit approval and preserved provenance.
- NOOP when the source adds no durable knowledge.

Contradictions preserve both claims and create
`queues/contradictions/<claim-pair>.json`. For changing facts, close the old
validity interval and add the new claim. Never rewrite history to make the
current statement look timeless.

## Compile and check

Patch focused pages; do not regenerate the vault. Update citations, related
links, claim ledger, aliases, and index entries together. Unknown types or
predicates enter `ontology/candidates.yaml`.

Queue knowledge-bearing edits for review. After approval, validate and run
relevant evaluation questions. Append an operation record with source hashes,
decisions, changed artifacts, validation result, and review disposition.
