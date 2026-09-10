# {{WIKI_NAME}} Wiki Contract

Purpose: {{PURPOSE}}

This is an agent-maintained, cross-project knowledge vault. Humans curate
sources and approve consequential knowledge changes. Agents maintain the
compiled wiki, claim graph, links, and indexes.

## Canonical layers

- `raw/` is immutable evidence. Add sources and manifest records; never rewrite
  source content after ingest.
- `wiki/` is compiled Markdown. Keep pages focused, cited, and connected with
  `[[wikilinks]]`.
- `claims/` is the typed claim graph. Claims preserve provenance, lifecycle,
  and temporal validity.
- `ontology/` defines accepted types, predicates, and aliases. Unknown
  vocabulary enters `ontology/candidates.yaml`.
- `queues/` holds proposed ingest, review, and contradiction work.
- `indexes/` contains rebuildable projections only.

Every compiled page has YAML frontmatter with a stable `id`, accepted `type`,
created and updated dates, source IDs, and tags.

## Knowledge boundary

Deterministic metadata, link, and generated-index maintenance may apply
automatically. New claims, contradictions, entity merges, destructive changes,
and ontology changes require review.

Every load-bearing claim must reach immutable evidence through a source ID and
anchor. Supersede changing facts; do not erase history. Abstain when the vault
lacks evidence.

## Operations

Read `KNOWLEDGE.md` first. Read `WIKI-OPERATIONS.md` only when running ingest,
query, lint, evaluation, ontology, or journal workflows. Run
`python3 scripts/wiki-check.py .` before publishing changes.
