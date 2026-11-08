# Findings shape

`render_report.py` reads this JSON and rejects a missing key, a duplicate or
non-integer `id`, an unknown `strength` or bead `type`, a `priority` outside
0-4, or a `top` that names no candidate.

```json
{
  "repo": "acme-shop",
  "scope": "ordering, chosen from hotspots",
  "top": 1,
  "top_reason": "Every order change touches it; deepening it removes three shallow modules.",
  "candidates": [
    {
      "id": 1,
      "title": "Deepen the Order intake module",
      "strength": "strong",
      "files": ["src/ordering/intake", "src/ordering/validation"],
      "problem": "Placing an Order goes through four shallow modules ...",
      "solution": "Merge them behind one interface that takes a draft Order ...",
      "benefits": "Locality: ... Leverage: ... Tests move to the intake interface ...",
      "rules": ["utils module: a domain without a name"],
      "adr_conflict": "Contradicts ADR-0007, but worth reopening because ...",
      "before": "graph LR\n  API --> Validate --> Price --> Persist",
      "after": "graph LR\n  API --> Intake[Order intake]",
      "bead": {"title": "Deepen Order intake", "type": "task", "priority": 2}
    }
  ],
  "glossary": [
    {"term": "Order", "definition": "A customer's request to buy products.", "avoid": ["Purchase"]}
  ]
}
```

- `strength`: `strong`, `worth-exploring`, or `speculative`.
- `files`: modules or directories, coarse enough to stay true for a while.
- `benefits`: in terms of locality, leverage, and what tests would look like.
- `rules`, `adr_conflict`, `glossary`: optional. A glossary entry needs
  `term` and `definition`.
- `before`/`after`: Mermaid, graph-shaped (dependencies, calls, sequences).
  Draw the same scope in both so the change is visible.
- `id`: an integer, unique.
- `bead.type`: `task`, `feature`, `bug`, `chore`, `spike`, `story`, or
  `decision`; `bead.priority`: an integer, 0 (highest) to 4. Use `spike` for
  `speculative` candidates.

The script prints the `bd create` commands (one epic, then a child per
candidate, each under `# candidate <id>`) after the report path. Run the epic
command and the chosen children in one shell call: shell state does not carry
between calls, so `$EPIC` would be empty.
