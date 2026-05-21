# AGENTS.md

This repository is a tool-agnostic skill pack. Installable content lives only
under `payload/`. Root-level files are for maintaining this repository.

Do not require package managers, host-specific package metadata, generated output
trees, or versioned workflows.

## Boundary

- `payload/skills/` - reusable skills intended for global or project install.
- `payload/rules/` - reusable rules intended for global or project install.
- `payload/hooks/` - hook authoring instructions intended for global or project
  install.
- Root-level `AGENTS.md`, `README.md`, `scripts/`, and future root-level
  `skills/`, `rules/`, or `hooks/` are repository-maintenance files. Do not
  install them into a target unless the user explicitly asks.

## Integrate

1. Identify the target project or global agent config the user wants to modify.
2. Check the latest documentation for the host coding tool before changing any
   config. Use the Context7 MCP server first when it is available; otherwise use
   official docs or the host tool's own help output.
3. Inspect existing skills, rules, hooks, and agent instruction files in the
   target.
4. Treat `payload/` as the only installable source. Do not install root-level
   repository-maintenance files.
5. Prefer symlinks from this repository into the host tool's native locations.
   Use copies only when symlinks are unsupported or the user asks for a portable
   install.
6. Link or copy these source directories as the host tool supports them:
   `payload/skills/`, `payload/rules/`, and `payload/hooks/`.
7. If legacy package or index config exists from a previous install, remove only
   entries that clearly reference this repository.
8. Preserve user-owned config. Before editing JSON, TOML, YAML, or Markdown
   config, make a timestamped backup beside the original.
9. Verify the host tool can discover the installed skills, rules, or hooks.
10. Report every path created, changed, skipped, removed, or backed up.

## Cleanup

1. Check the latest documentation for the host coding tool before changing
   config. Use Context7 MCP first when available.
2. Inspect the target for symlinks, copied directories, and config entries that
   point to this repository or to files under `payload/`.
3. Remove only paths or config entries that clearly reference `killall-skills`.
4. Leave user-authored files alone unless they are exact copies of files from
   this repository.
5. Restore backups only when the user explicitly asks or the current config is
   broken.
6. Report every path removed, preserved, or requiring manual review.

## Hook Contract

- Hook instructions live under `payload/hooks/`.
- Hook phases are `pre-session/`, `pre-tool/`, `post-tool/`, and
  `post-session/`.
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
