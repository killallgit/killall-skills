# Codex Marketplace Compatibility

Status: complete

## Goal

Expose the repository's skills as installable Codex marketplace plugins while
preserving individual skill installation through the cross-agent `skills` CLI.

## Distribution

- `.agents/plugins/marketplace.json` defines the `killallgit` marketplace.
- `planning`, `engineering`, `knowledge`, and `experimental` are independent
  plugins under `plugins/<domain>/`.
- Each plugin has a portable root `plugin.json`, a Codex compatibility manifest
  at `.codex-plugin/plugin.json`, and its canonical skills under `skills/`.
- The repository-level `agents/` and opt-in `hooks/voice-readback/` remain
  outside the plugins. Installing a skill plugin does not register hooks or copy
  Claude-specific subagents.

## Validation

- Every Codex compatibility manifest passes the `plugin-creator` validator.
- Every portable manifest passes the Agent Plugins JSON schema.
- Automated tests cover marketplace inventory, paths, policy fields, manifest
  identity, and plugin skill inventory.
- The full Python test suite passes.
- The cross-agent `skills` CLI discovers all nine skills.
