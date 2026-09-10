# Query

## Classify

Choose the smallest retrieval shape:

- entity lookup;
- thematic synthesis;
- cross-project comparison;
- relationship or multi-hop path;
- historical or "as of" question.

## Retrieve

Use the configured retrieval option. Prefer exact lexical search for IDs,
symbols, names, and quoted language. Use qmd or another configured semantic
projection for fuzzy themes. Search results are leads; open full pages and
claims before relying on them.

Traverse only relevant typed relationships. For historical questions, filter
claims by both world validity (`valid_from`, `valid_to`) and observation time
(`observed_at`). Open supporting raw evidence for load-bearing details. Never
answer from an index snippet, generated embedding, or graph edge alone.

## Answer

Synthesize from the compiled wiki and cite pages plus source IDs or anchors.
Separate current truth, historical truth, disputes, and inference. If evidence
is absent or conflicting, say so and identify the missing source or review
needed.

For comparisons, use a table when it makes repeated fields clearer. For
relationship questions, state the typed path and its evidence. Avoid copying
large source passages.

## Compound

If the answer creates reusable synthesis, propose:

- ADD a focused concept, flow, comparison, or question page;
- UPDATE an existing page;
- queue new claims or links for review;
- NOOP when the answer is transient.

Do not file chat text verbatim. Compile the durable insight with citations,
validate it, and add a representative evaluation question when the query
exposed a retrieval gap.
