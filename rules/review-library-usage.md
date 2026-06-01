---
description: Verify third-party library and SDK API usage against current docs
globs: ["**/*"]
---
# Review Library Usage

When writing or reviewing code that uses a third-party library, framework, SDK,
service API, or config schema, verify the API contract against current docs.

## Rule

Do not assume external API usage from memory when the exact method, option,
schema, or initialization pattern matters.

## Lookup order

1. Use Context7 MCP first when available: resolve the library id, then query the
   exact API surface.
2. If Context7 is unavailable or incomplete, use web search/open against the
   official docs or source repository docs.
3. If the installed local version is the authority, inspect local type
   declarations, generated docs, source code, or tool `--help`.

## Applies to

- SDK/client-library calls.
- Framework APIs and lifecycle hooks.
- Build tool, provider, plugin, and service config schemas.
- Third-party package usage during implementation or code review.
- Errors that suggest API drift or deprecated options.

## Does not apply to

- Routine shell commands, local repo inspection, or git porcelain.
- Code owned by the current repo; read the source directly.
- Conceptual explanations that do not depend on exact API shape.

## Report pattern

State the verified API surface, cite the source, then compare docs to local
usage. If docs cannot be verified, say so and name the remaining risk.
