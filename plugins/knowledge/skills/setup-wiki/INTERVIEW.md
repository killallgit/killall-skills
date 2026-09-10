# Setup Interview

Discover first, then ask only decisions that cannot be inferred safely. Ask one
question at a time. Explain unfamiliar vocabulary in one sentence and lead with
the recommended default.

## 1. Purpose

Ask what the wiki should help people or agents understand, decide, or answer.
Collect three to five representative questions. These seed
`evals/questions.yaml` after setup.

## 2. Name and projects root

Propose `<projects-root>/<name>-wiki`. A projects root is the obvious directory
whose children are the repositories in scope. Prefer `../<name>-wiki` when the
current repository is already one direct child. Do not put the vault inside one
member repository.

## 3. Scope

Show nearby repositories and ask which belong. Record absolute roots. Ask about
excluded repositories, subtrees, generated outputs, dependencies, worktrees,
secrets, credentials, and personal scratch files.

## 4. Sources and ownership

Ask which inputs may feed the wiki: repositories, documents, URLs, issue
trackers, meeting notes, transcripts, chat exports, or a manual drop folder.
Separate:

- immutable evidence copied or referenced under `raw/`;
- human-owned notes that agents may cite but not rewrite;
- agent-maintained compiled pages under `wiki/`.

## 5. Audience and sensitivity

Ask whether the vault is personal, team, or public. Record sensitivity labels,
retention constraints, excluded material, external-model restrictions, and who
may approve knowledge changes.

## 6. Freshness

Ask which facts change, what "current" means, and review intervals. Recommend
claim-level `observed_at`, plus `valid_from` and `valid_to` for changing facts.

## 7. Domain model

Explain that the ontology is a small vocabulary of allowed entity types,
relationships, aliases, and constraints. Offer:

- start with universal types and learn candidates during ingest (recommended);
- seed domain types and predicates now;
- adopt an existing glossary or ontology.

Unknown vocabulary belongs in `ontology/candidates.yaml`; setup does not invent
a large taxonomy.

## 8. Retrieval and projections

Default to Markdown, wikilinks, and lexical search. Offer qmd when installed.
Offer embeddings, JSON-LD/RDF, GraphRAG, Graphiti, or a graph database only as a
rebuildable projection with a demonstrated need.

## 9. Automation

Default to the hybrid boundary:

- deterministic metadata, link, and index maintenance may apply;
- claims, contradictions, entity merges, destructive changes, and ontology
  changes enter review queues.

Ask which detected hosts may receive SessionStart and SessionEnd hooks.

## 10. Git policy

Offer:

- `manual` — user controls commits and remotes;
- `direct` — agents may commit approved wiki changes and push safely;
- `reviewed` — changes land through branches or pull requests.

Never create a remote from a guess.

## Confirmation

Show every answer plus the exact paths that setup will create or modify.
Separate vault writes, project-pointer writes, Git initialization, and user
config hook registration. One confirmation may authorize the displayed set;
anything added later requires another confirmation.

For an existing vault, inventory it first. Preserve its contract and content,
explain conflicts, and propose a merge. Never treat "setup" as permission to
replace an existing knowledge base.
