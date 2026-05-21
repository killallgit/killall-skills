# AGENTS.md

This repository is a tool-agnostic skill pack. Do not require package managers,
host-specific package metadata, generated output trees, or versioned workflows.

## Integrate

1. Identify the target project or global agent config the user wants to modify.
2. Check the latest documentation for the host coding tool before changing any
   config. Use the Context7 MCP server first when it is available; otherwise use
   official docs or the host tool's own help output.
3. Inspect existing skills, rules, hooks, and agent instruction files in the
   target.
4. Prefer symlinks from this repository into the host tool's native locations.
   Use copies only when symlinks are unsupported or the user asks for a portable
   install.
5. Link or copy these source directories as the host tool supports them:
   `skills/`, `rules/`, and `hooks/`.
6. If legacy package or index config exists from a previous install, remove only
   entries that clearly reference this repository.
7. Preserve user-owned config. Before editing JSON, TOML, YAML, or Markdown
   config, make a timestamped backup beside the original.
8. Verify the host tool can discover the installed skills, rules, or hooks.
9. Report every path created, changed, skipped, removed, or backed up.

## Cleanup

1. Check the latest documentation for the host coding tool before changing
   config. Use Context7 MCP first when available.
2. Inspect the target for symlinks, copied directories, and config entries that
   point to this repository.
3. Remove only paths or config entries that clearly reference `killall-skills`.
4. Leave user-authored files alone unless they are exact copies of files from
   this repository.
5. Restore backups only when the user explicitly asks or the current config is
   broken.
6. Report every path removed, preserved, or requiring manual review.

## Hook Contract

- Hooks live under `hooks/pre-session/`, `hooks/pre-tool/`,
  `hooks/post-tool/`, and `hooks/post-session/`.
- Hook scripts must be host-neutral. They may read common environment variables,
  stdin, or optional arguments.
- Hook scripts should emit agent-readable guidance and exit 0 when context is
  unavailable.

## Safety

- Never delete ambiguous files.
- Never overwrite user config without a backup.
- Never assume host-tool config paths from memory; check current docs first.
- Keep integration reversible and scoped to `killall-skills`.

## Validation

Run:

```bash
bash scripts/validate.sh
```
