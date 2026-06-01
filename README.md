# killall-skills

A plain collection of tool-agnostic agent content:

- `skills/` — reusable skills (one `SKILL.md` per directory)
- `rules/` — reusable behavioral rules (one Markdown file each)
- `hooks/` — lifecycle hook scripts (conventions in `hooks/README.md`)

No installer, no packaging. To set it up, point a coding agent at this repo:

> Read `AGENTS.md` and install the skills, rules, and hooks into my coding tool.

`AGENTS.md` has the per-host install recipe (symlink/copy + verify).

## License

MIT
