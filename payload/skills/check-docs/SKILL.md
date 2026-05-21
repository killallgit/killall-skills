---
name: check-docs
description: Fetch current upstream documentation before providing CLI commands, install steps, config schemas, or API usage for any third-party tool, library, SDK, or cloud service. Use when the user asks "how do I...", "what's the command for...", or when about to suggest an install/config flow. Triggers automatically before any non-trivial external-tool command.
---

# Check Latest Docs Before Commanding

## Why

Memorized command syntax is a hypothesis, not a fact. Tools rename flags, restructure subcommands, and deprecate APIs between releases. Giving stale syntax wastes the user's time, breaks their cluster, or worse.

## When to invoke

Before producing any of:
- CLI invocations (kubectl, helm, talm, talosctl, gh, terraform, gcloud, aws, az, etc.)
- Install/setup procedures
- Config schemas (Kubernetes manifests, Helm values, ConfigMaps)
- SDK/library API calls when version is unknown or known to have changed recently

## When NOT to invoke

- POSIX/shell utilities (`ls`, `grep`, `find`, `awk`, `sed`)
- Git porcelain (`git commit`, `git push`)
- Code in the user's own repo (read it)
- Conceptual answers ("what does X mean")

## Workflow

### 1. Identify target

State out loud:
- Tool/library/service name
- Version (if known from user's repo, lockfile, or message)
- Exact subcommand or API surface in question

### 2. Fetch docs

Priority order:

1. **`context7` MCP** — `mcp__plugin_context7_context7__resolve-library-id` then `query-docs`. Best for libraries, frameworks, SDKs, well-known CLIs. Cite the returned URL.
2. **`WebFetch`** — when context7 has no entry. Hit the canonical docs URL directly (e.g. `cozystack.io/docs/`, `kubernetes.io/docs/reference/`, `cloud.google.com/sdk/gcloud/reference/`).
3. **Tool's own `--help`** — when the tool is installed and you can run it. `<tool> <subcommand> --help` is authoritative for flags.
4. **`gh search`** / repo `README.md` / `docs/` — for niche tools without docs sites.

Do **not** fall back to training-data syntax silently. If all three sources fail, tell the user "I can't verify this command — please check the docs at <URL>".

### 3. Cite the source inline

Bad:
> Run `talm apply -f node-2.yaml -i`

Good:
> Per [cozystack.io/docs/operations/cluster/scaling](https://cozystack.io/docs/operations/cluster/scaling):
> ```
> talm apply -f nodes/nodeN.yaml -i
> ```

The user can then judge whether the source is current.

### 4. Note version sensitivity

If the docs you fetched are for a different version than the user's tool, flag it:
> "Docs are for talm v0.18; your `talm.lock` shows v0.16. Behavior may differ on `--mode`."

## Anti-patterns

❌ "Off the top of my head, the command is..."
❌ Producing flags from memory without citation
❌ Recovering from a wrong command by guessing again
❌ "It should be something like..."

## Pattern

✅ "Let me check current docs first." → fetch → cite → command
✅ "Docs unclear on this — running `<tool> --help` to confirm."
✅ "I'm not finding authoritative docs for this. Best guess + risk: ..."

## Recovery when caught wrong

If user reports a command failed:
1. Apologize briefly. No fluff.
2. Re-fetch docs.
3. Diff old vs. new syntax. State what changed.
4. Provide corrected command + citation.
5. Proceed.
