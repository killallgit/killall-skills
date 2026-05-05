---
description: Verify against latest official docs before providing CLI commands, install steps, or API usage
globs: ["**/*"]
---
# Verify Before Commanding

Before giving the user any CLI command, install step, config snippet, or API call for an external tool/library/SDK/CLI/cloud service: confirm the syntax against current upstream documentation.

## Rule

**Do not produce commands from training-data memory alone.** Tools rename flags, restructure subcommands, deprecate APIs, and rewrite install flows between releases. Memorized syntax is a guess, not a citation.

## When this applies

- Install/setup instructions (`helm install`, `kubectl apply`, package manager flows)
- CLI invocations for any third-party tool (talm, talosctl, gh, kubectl, helm, terraform, ansible, etc.)
- SDK/library API calls when version is unknown or recently changed
- Cloud provider CLIs (gcloud, aws, az)
- Config schemas (Kubernetes resources, Helm values, etc.)

## When this does not apply

- Code in the user's repo (read it directly)
- Standard POSIX/shell utilities (`ls`, `grep`, `awk`)
- Git porcelain commands (`git commit`, `git status`)
- Trivial questions where the answer is conceptual, not syntactic

## How to comply

1. Identify the tool, version (if known), and exact subcommand the user is asking about
2. Fetch current docs via `context7` (preferred) or `WebFetch` against the canonical docs URL
3. Quote the relevant snippet or cite the URL when presenting commands
4. If docs unavailable or unclear, say so — do not guess

## Anti-pattern

> "Run `talm template -e <ip> -n <ip> templates/worker.yaml > nodes/node-2.yaml`"

Missing `-t` and `-i`. Source: training data. Caused user rework.

## Correct pattern

> Per cozystack.io/docs/operations/cluster/scaling:
> ```
> talm template -e <ip> -n <ip> -t templates/worker.yaml -i > nodes/nodeN.yaml
> ```

Source cited. Flags verified.
