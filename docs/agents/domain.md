# Optional Context Docs

Context/glossary docs are optional. Only use them when the repo benefits from a shared vocabulary or explicit domain language.

## Before exploring, read these if they exist

- **`docs/CONTEXT.md`** or
- **`docs/CONTEXT-MAP.md`** if the repo has multiple contexts
- **`docs/adr/`** for durable architectural decisions

If none of these files exist, proceed silently. Do not force the repo into ceremony it does not need.

## File structure

Single-context repo:

```text
docs/
  CONTEXT.md
  adr/
```

Multi-context repo:

```text
docs/
  CONTEXT-MAP.md
  adr/
src/
  ordering/
    docs/
      CONTEXT.md
      adr/
  billing/
    docs/
      CONTEXT.md
      adr/
```

## Use the glossary only when it exists

When a glossary exists, use its vocabulary in issue titles, refactor proposals, test names, and architecture discussions.

If no glossary exists, do not invent one unless the user is clearly doing design or architecture work that would benefit from it.

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding it.
