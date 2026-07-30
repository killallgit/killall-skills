---
name: wiki
description: Operate a configured cross-project LLM wiki through source ingest, grounded query, claim reconciliation, lint, evaluation, journaling, ontology maintenance, and safe Git sync. Use when a project has a `.wiki.json` pointer or the user asks to ingest, query, maintain, lint, or update a shared knowledge vault.
---

# Wiki

Use the compiled wiki for durable cross-project intent, history, decisions, and
synthesis. Use source repositories and external systems for live state and
procedural skills for operational commands.

## Orient

1. Resolve the vault from an explicit path or the nearest `.wiki.json` while
   walking from cwd to its Git root. If none exists, look only among immediate
   siblings under the projects root. If zero or several match, ask; do not scan
   the whole home directory.
2. Read `<vault>/wiki.json`, `<vault>/AGENTS.md`, and bounded
   `<vault>/KNOWLEDGE.md`.
3. Honor project roots, exclusions, sensitivity, audience, review boundary, and
   Git policy.
4. If the vault is Git-backed and clean, pull only with `--ff-only`. If dirty,
   skip pulling and preserve in-flight work.
5. Classify the request: ingest, query, lint/evaluate, ontology, or journal.

## Run one bounded workflow

- Source integration: [INGEST.md](./INGEST.md)
- Questions and synthesis: [QUERY.md](./QUERY.md)
- Lint, evaluation, ontology, journal, and projections:
  [MAINTENANCE.md](./MAINTENANCE.md)

Load `<vault>/WIKI-OPERATIONS.md` for operational detail. Do not preload
`raw/`, read the whole claim ledger, or open unrelated pages.

## Finish

1. Run `python3 <vault>/scripts/wiki-check.py <vault>`.
2. Record the operation in `runs/log.jsonl`; journal durable session outcomes.
3. Refresh `KNOWLEDGE.md` only with bounded, currently useful context.
4. Follow the configured Git policy. Stage only files this workflow changed.
   Never force, sweep unrelated edits, or overwrite a rejected push.
5. Report evidence used, pages/claims changed, queued reviews, validation
   findings, and unsynced work.

When a workflow would load more than five substantial file or tool outputs,
delegate bounded reading if the host and user permit it; the main context
receives decisions and citations, not raw dumps.
