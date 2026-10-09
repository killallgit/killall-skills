# Disable plugins and skills per project

Covers Claude Code, Codex, and Cursor. Each host has different controls. Only Claude Code and Codex have a per-project plugin switch. Only Claude Code has a per-project skill switch.

| Host | Plugin, per project | Skill, per project |
| --- | --- | --- |
| Claude Code | `enabledPlugins` in `.claude/settings.local.json` | `skillOverrides` in `.claude/settings.local.json` |
| Codex | `[plugins."<name>@<marketplace>"]` in `.codex/config.toml` | None. Use `~/.codex/config.toml` with the skill's absolute path |
| Cursor | None. Uninstall, or install at project scope | None. Edit the skill's frontmatter |

In every host, merge new keys into the existing config. Do not replace the file.

## Claude Code

Choose the file by who the change is for.

| File | Who it applies to | Committed |
| --- | --- | --- |
| `.claude/settings.local.json` | Only you, in this project | No (gitignored) |
| `.claude/settings.json` | Everyone who clones the repo | Yes |

Use `.claude/settings.local.json` by default. Use `.claude/settings.json` only when the user asks for a team-wide change. Precedence, highest first: managed settings, `--settings`, `.claude/settings.local.json`, `.claude/settings.json`, `~/.claude/settings.json`.

```json
{
  "enabledPlugins": {
    "formatter@your-org": false
  },
  "skillOverrides": {
    "deploy": "off"
  }
}
```

Or disable the plugin with the CLI:

```bash
claude plugin disable formatter@your-org --scope local    # only you, this project
claude plugin disable formatter@your-org --scope project  # committed, whole team
```

- Plugin keys use the format `<plugin>@<marketplace>`. Disabling a plugin also disables the skills it provides.
- A `false` in `~/.claude/settings.json` does not override a project `true`. Put the `false` in `.claude/settings.local.json`.
- A plugin enabled or disabled in managed settings cannot be changed.
- `skillOverrides` values: `"on"` (default), `"name-only"`, `"user-invocable-only"`, `"off"`. Entries match by skill name. They apply to personal skills in `~/.claude/skills` and to project skills, not to plugin skills.
- To stop Claude from invoking a skill, add `"permissions": { "deny": ["Skill(deploy)"] }`. `Skill(deploy *)` also matches calls with arguments. A bare `Skill` blocks all skills.
- To disable all bundled skills, set `"disableBundledSkills": true`.
- Do not use `disableSkills`. That setting does not exist.

Verify: `claude plugin list`, or `/plugin` and `/skills` in a session.

## Codex

Project config is `.codex/config.toml`. Codex reads it only when the project is trusted (`projects."<path>".trust_level = "trusted"` in `~/.codex/config.toml`). Project config overrides `~/.codex/config.toml`. CLI flags and `-c` overrides beat both.

Disable a plugin for this project:

```toml
# .codex/config.toml
[plugins."formatter@your-org"]
enabled = false
```

- This disables the plugin without uninstalling it.
- It does not override plugins that a workspace admin manages.
- To disable one MCP server inside a plugin, use `[plugins."formatter@your-org".mcp_servers.<server>]` with `enabled = false`.
- The `/plugins` menu in the TUI writes to `~/.codex/config.toml`, which applies to every project. Edit `.codex/config.toml` by hand for a per-project change.

Codex ignores `[[skills.config]]` in a project `.codex/config.toml`. To disable one skill, add the entry to `~/.codex/config.toml` with the skill's absolute path. The path makes the entry apply to that repo only. Restart Codex afterwards.

```toml
# ~/.codex/config.toml
[[skills.config]]
path = "/abs/path/to/repo/.agents/skills/deploy/SKILL.md"
enabled = false
```

- To disable bundled system skills, set `[skills.bundled]` with `enabled = false`. The source code shows this works in a project config. The docs do not say.
- To stop Codex from invoking a skill on its own, set `policy.allow_implicit_invocation: false` in the skill's `agents/openai.yaml`. An explicit `$deploy` still runs it.

Verify: `/skills` and `/plugins` in the TUI.

## Cursor

Cursor has no per-project setting to disable a plugin or a skill. Use these controls instead.

Skills: edit the frontmatter in the skill's `SKILL.md`.

```yaml
---
name: deploy
description: Deploy the app to staging.
disable-model-invocation: true   # agent does not apply it on its own; /deploy still runs it
paths:                           # or limit it to matching files
  - "apps/web/**"
---
```

- Cursor loads skills from `.agents/skills/`, `.cursor/skills/`, `.claude/skills/`, and `.codex/skills/`, plus the same folders under `~`.
- There is no switch to disable all skills. Do not rename skill folders unless the user asks.

Plugins: Cursor has no enable/disable switch for a plugin. Uninstall the plugin, or install it at project scope instead of user scope. Use **Customize** in the editor or `/plugin` in the CLI. A plugin an admin marks "Required" cannot be uninstalled.

Claude Code and Codex content: the editor setting **Cursor Settings → Agents → Third-Party Imports** turns off every imported plugin, skill, rule, and MCP server at once. It is UI-only, the Cursor CLI ignores it, and the docs do not say whether it applies per workspace.

MCP servers: toggle them in **Customize → MCPs**, or run `agent mcp disable <server>` in the CLI.

## Sources

- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/plugins/loading
- https://code.claude.com/docs/en/plugins/cli-reference
- https://code.claude.com/docs/en/skills
- https://learn.chatgpt.com/docs/config-file/config-basic
- https://learn.chatgpt.com/docs/config-file/config-reference
- https://learn.chatgpt.com/docs/build-skills
- https://learn.chatgpt.com/docs/plugins
- https://developers.openai.com/codex/plugins/build.md
- https://github.com/openai/codex/blob/main/codex-rs/config/src/skills_config.rs
- https://cursor.com/docs/skills.md
- https://cursor.com/docs/plugins.md
- https://cursor.com/docs/reference/third-party-hooks.md
- https://cursor.com/docs/mcp.md
