# Agent skill and plugin distribution

## Question

How should a public skills repository let users install one skill or one plugin
at a time in Claude Code and Codex without requiring one repository per skill?

## Current host behavior

Claude Code marketplaces are catalogs of independently installable plugins. A
single marketplace can list many plugin entries, and every entry has its own
source directory or repository. Installation selects a plugin, not a skill
inside that plugin. Skills bundled in the selected plugin are installed
together and use the plugin namespace. Claude also supports standalone skills
under `.claude/skills/` or `~/.claude/skills/`.

Sources:

- [Claude Code: create and distribute a plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
- [Claude Code: discover and install plugins](https://code.claude.com/docs/en/discover-plugins)
- [Claude Code: plugins reference](https://code.claude.com/docs/en/plugins-reference)

Codex likewise installs a marketplace plugin as a unit. Its bundled skill
installer separately supports installing one or more skill directories from a
GitHub repository path into `$CODEX_HOME/skills`, which defaults to
`~/.codex/skills`.

Sources:

- [Codex plugin creator and marketplace entry format](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/plugin-creator/SKILL.md)
- [Codex skill installer](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/skill-installer/SKILL.md)

The open Agent Skills standard defines a skill as a self-contained directory
with `SKILL.md` and optional resources. It standardizes the skill format, not a
cross-client plugin package or dependency system.

Source: [Agent Skills specification repository](https://github.com/agentskills/agentskills)

## Public repository patterns

| Repository | Repository unit | Skill install unit | Plugin install unit | Pattern |
| --- | --- | --- | --- | --- |
| [Anthropic Claude Code](https://github.com/anthropics/claude-code/blob/main/.claude-plugin/marketplace.json) | One marketplace monorepo | Skills live inside plugins | One marketplace entry such as `code-review` or `plugin-dev` | Many plugin directories in one repository |
| [Anthropic Skills](https://github.com/anthropics/skills) | One skills monorepo | Self-contained skill directories | Two curated bundles, `document-skills` and `example-skills` | Raw skills plus a small number of coherent bundles |
| [Elastic Agent Skills](https://github.com/elastic/agent-skills) | One skills monorepo | `npx skills add elastic/agent-skills --skill <name>` | Domain bundles such as Elasticsearch, Kibana, Observability, Security, and Cloud | Hybrid per-skill and per-domain-plugin distribution |
| [NVIDIA Skills](https://github.com/nvidia/skills) | One catalog monorepo | `npx skills add nvidia/skills --skill <name> --agent <agent>` | No plugin boundary required for the common flow | Cross-agent, skill-first catalog |
| [Microsoft Power Platform Skills](https://github.com/microsoft/power-platform-skills) | One marketplace monorepo | Skills are contained in domain plugins | One plugin per product area, each with its own skills, agents, and shared files | Domain plugin directories with independent installation |
| [Hugging Face Skills](https://github.com/huggingface/skills) | One skills monorepo | Most skills use `hf skills add <name>` | The public Claude marketplace intentionally exposes only the `hf-cli` bootstrap plugin | Small bootstrap plugin plus dynamic skill catalog |
| [Block Agent Skills](https://github.com/block/agent-skills) | One catalog monorepo | `npx skills add ... --skill <name>` | Not required for the primary flow | Flat public skill catalog |

The clearest match is Elastic. It warns users not to install every skill because
each installed skill contributes routing metadata, exposes a handful of
cohesive native plugins, and also supports selecting a single skill through the
cross-agent installer. See [Elastic's installation guidance](https://github.com/elastic/agent-skills#readme).

The `skills` CLI used by Elastic, NVIDIA, and Block supports Git repositories,
direct paths, `--skill`, multiple `--agent` targets, project or global scope,
copy or symlink installation, listing, updating, and removal. It recognizes
Claude marketplace manifests as skill discovery sources.

Source: [vercel-labs/skills CLI documentation](https://github.com/vercel-labs/skills/blob/main/README.md)

## Repository implementation

The repository exposes five native plugins: planning, engineering,
architecture, knowledge, and experimental. Each domain directory is a complete
Claude Code and Codex plugin containing its own manifests, skills, and optional
agents. The shell installer accepts selected domains or an explicit `--all`.

The same repository is an individual-skill catalog. List its available skills
with:

```bash
npx skills@latest add killallgit/killall-skills --list
```

A single skill can therefore be installed globally into both hosts now:

```bash
npx skills@latest add killallgit/killall-skills \
  --skill research \
  --agent claude-code \
  --agent codex \
  --global \
  --yes
```

This path installs only the selected skill directory. It does not install
plugin-only components such as Claude subagents or companion resources outside
that skill directory.

The canonical layout is:

```text
plugins/
  planning/
    .claude-plugin/plugin.json
    .codex-plugin/plugin.json
    skills/
  architecture/
    .claude-plugin/plugin.json
    .codex-plugin/plugin.json
    skills/
  engineering/
  knowledge/
  experimental/
.claude-plugin/marketplace.json
.agents/plugins/marketplace.json
```

The root marketplaces list each directory as a separate plugin source. The
cross-agent skills CLI can discover the nested skills through the marketplace
metadata, preserving single-skill installation without duplicating their
contents.
