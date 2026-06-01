---
name: review-library-usage
description: Verify third-party library, framework, SDK, or service API usage against current docs before implementing or reviewing code. Use when code imports an external package, calls an SDK/API, configures a framework integration, or when the user asks whether library usage is correct.
---

# Review Library Usage

Use this to confirm that code is using an external API correctly. The goal is
not to look up every command before speaking; it is to avoid stale assumptions
about third-party libraries, frameworks, SDKs, service APIs, and config schemas.

## When to invoke

- Reviewing or writing code that imports a third-party package.
- Calling an SDK, cloud API, client library, plugin API, or framework API.
- Changing framework configuration, build tool config, provider schemas, or
  integration setup where docs define the contract.
- Debugging errors that look like API drift, deprecated options, changed return
  shapes, or incorrect initialization.
- The user asks whether usage of a library or API is correct.

## When not to invoke

- Routine shell/POSIX commands, local file inspection, or git porcelain.
- Code in the user's repo where the source itself is authoritative.
- Simple conceptual explanations that do not depend on exact API shape.
- Commands already verified by local `--help` output and not tied to a library
  API contract.

## Workflow

### 1. Identify the API surface

State the target precisely:

- library/framework/service name
- package name and version, from lockfiles or manifests when available
- exact method, config key, CLI subcommand tied to an API contract, or schema
  being reviewed
- the local code path using it

### 2. Fetch authoritative docs

Use this lookup order:

1. **Context7 MCP, if available** — resolve the library id, then query docs for
   the exact API surface. Prefer this for libraries, frameworks, SDKs, and
   well-known CLIs. Cite the returned URL or library id.
2. **Web search / official docs fallback** — if Context7 is unavailable, has no
   entry, or lacks the needed version/API surface, search/open the official docs
   or source repository docs. Prefer canonical docs over blog posts.
3. **Local tool help or source** — use `<tool> <subcommand> --help`, type
   declarations, generated docs, or source code when those are the authority for
   the installed version.

Do not silently fall back to training-data syntax. If no authoritative source is
available, say what could not be verified and treat the proposed usage as a
risk.

### 3. Compare docs to local usage

Check the actual code/config against the docs:

- required initialization and provider setup
- method names, arguments, return values, async behavior, and error handling
- config key names, nesting, defaults, and version-specific changes
- deprecations and migration notes
- examples in the docs that match the local usage pattern

### 4. Report findings

Keep the output actionable:

- **Correct** — cite the doc and explain why the local usage matches.
- **Incorrect** — cite the doc, identify the mismatch, and patch or recommend
  the smallest correction.
- **Unverified** — name the source attempted and the remaining risk.

## Anti-patterns

- Triggering this skill before every command.
- Citing stale memory instead of current docs.
- Using a blog post when official docs or source are available.
- Declaring usage wrong without comparing against the installed version.
