# Shared understanding docs

Three files, each with one job. Create each only when there is something to
write. None should name file paths that will move.

## GLOSSARY.md: the shared language

Domain terms only. A general programming concept (timeout, retry, cache) does
not belong, even if the project uses it heavily. No implementation details.

```md
# {Context name}

{One or two sentences on what this context is.}

## Language

**Order**:
A customer's request to buy one or more products.
_Avoid_: Purchase, transaction
```

- Be opinionated: pick one word per concept and list the rest under _Avoid_.
- Define what it is, not what it does. One or two sentences.
- Group under subheadings when clusters emerge.
- A repo with several bounded contexts has a root `GLOSSARY-MAP.md` linking
  each context's `GLOSSARY.md` and saying how they relate (which events or
  shared types cross between them).

Write a term the moment it settles; don't batch. When a user's word conflicts
with the glossary, ask which they mean. When the code conflicts with what the
user says, show them the code.

## ARCHITECTURE.md: the map

Short and stable (after matklad's ARCHITECTURE.md). Sections:

1. **Bird's eye view**: the problem the system solves, in a paragraph.
2. **Codemap**: the coarse modules, what each owns, how they connect. Name
   modules, not files. A C4 context or container diagram in Mermaid fits here.
3. **Invariants**: what must stay true, especially things that are absent
   ("the domain never imports the HTTP layer").
4. **Cross-cutting concerns**: errors, config, testing, observability.

Revise it rarely. If it changes with every PR, it is too detailed.

## docs/adr/NNNN-title.md: decisions

Offer an ADR only when all three hold: hard to reverse, surprising without
context, and the result of a real trade-off. A rejected candidate qualifies
when its reason would stop a future review from suggesting it again.

```md
# NNNN. {Decision as a short statement}

Status: accepted | superseded by NNNN

## Context
{The forces at play and the options considered.}

## Decision
{What we chose.}

## Consequences
{What becomes easier, what becomes harder.}
```
