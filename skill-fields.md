# SKILL.md fields by harness

YAML frontmatter at the top of `SKILL.md`. The portable set is the [Agent Skills spec](https://agentskills.io/specification). Each harness below either requires a field, accepts it, or leaves it undocumented.

| Mark | Meaning |
| --- | --- |
| req | Required |
| yes | Accepted and used |
| pass | Accepted; the harness does not act on the value |
| — | Not part of that harness's documented set |

| Field | Spec | Claude Code | Cursor | Codex | Copilot CLI |
| --- | --- | --- | --- | --- | --- |
| `name` | req | yes | req | req | req |
| `description` | req | yes | req | req | req |
| `license` | yes | pass | — | pass | yes |
| `compatibility` | yes | pass | — | — | — |
| `metadata` | yes | pass | yes | yes | — |
| `allowed-tools` | yes | yes | — | pass | yes |
| `when_to_use` | — | yes | — | — | — |
| `argument-hint` | — | yes | — | — | yes |
| `arguments` | — | yes | — | — | — |
| `disable-model-invocation` | — | yes | yes | — | yes |
| `user-invocable` | — | yes | — | — | yes |
| `disallowed-tools` | — | yes | — | — | — |
| `model` | — | yes | — | — | — |
| `effort` | — | yes | — | — | — |
| `context` | — | yes | — | — | — |
| `agent` | — | yes | — | — | — |
| `background` | — | yes | — | — | — |
| `hooks` | — | yes | — | — | — |
| `paths` | — | yes | yes | — | — |
| `globs` | — | — | yes | — | — |
| `shell` | — | yes | — | — | — |
| `icon` | — | — | yes | — | — |
| `color` | — | — | yes | — | — |

Codex does not take invocation policy from `SKILL.md`. That lives in `agents/openai.yaml`:

| Field | Required | Purpose |
| --- | --- | --- |
| `interface.display_name` | no | Name shown in the UI |
| `interface.short_description` | no | Short UI description |
| `interface.default_prompt` | no | Suggested prompt inserted when the skill is invoked |
| `policy.allow_implicit_invocation` | no | `false` keeps the skill from running unless the user invokes it |

The interface metadata is optional at runtime; a policy-only file is valid.
Plugin-submission checks may impose additional requirements and should be checked
separately from runtime parsing.

`metadata.short-description` in `SKILL.md` is the one metadata key the Codex parser reads. `allow_implicit_invocation: false` is the Codex counterpart of `disable-model-invocation: true`.

## Field notes

**`name`.** Spec: 1–64 characters, lowercase letters, digits, and hyphens, no leading, trailing, or doubled hyphen, and it must match the parent directory. Claude Code treats it as optional and defaults to the directory name. Cursor requires it and expects the same directory match. Codex caps it at 64 characters and requires it to be non-empty; the bundled validator also enforces hyphen-case. Copilot requires it, caps it at 64 characters, and allows letters, numbers, hyphens, underscores, dots, colons, and spaces, as long as it starts with a letter or number.

**`description`.** Spec: 1–1024 characters, what the skill does and when to use it. Claude Code recommends it and, if it is missing, uses the first non-empty body line. `description` plus `when_to_use` is truncated at 1,536 characters in Claude's skill listing. Codex requires a non-empty description and does not cap its length.

**`metadata`.** Spec: a map of string keys to string values. Claude Code stores the map and does not act on it. Cursor documents it as an arbitrary key-value map. Codex reads `short-description` from it.

**`allowed-tools`.** Spec marks this experimental: a space-separated list of tools the skill may use without a prompt. Claude Code also accepts a comma-separated string or a YAML list, and the grant lasts for the turn that invoked the skill. Copilot accepts a comma-separated string or a YAML array of its tool names, or `"*"` for every tool. Pre-approving `shell` or `bash` skips confirmation for terminal commands. The names each harness actually ships are in [Built-in tools](#built-in-tools).

**`paths`.** Globs that limit automatic activation. Claude Code and Cursor both accept a comma-separated string or a YAML list. Cursor's older name for the same field is `globs`.

**`disable-model-invocation`.** `true` loads the skill only when the user types `/name`. Default is automatic invocation. Cursor and Copilot use the same field. Codex uses `policy.allow_implicit_invocation` instead.

**`user-invocable` and `argument-hint`.** Claude Code and Copilot both accept these. `user-invocable: false` hides the skill from the `/` menu (default `true`). `argument-hint` is the autocomplete hint, such as `[issue-number]`.

**Claude-only behavior fields.** `context: fork` runs the skill in a subagent; `agent` picks the subagent type and `background: false` waits for that subagent in the same turn. `model` and `effort` (`low`, `medium`, `high`, `xhigh`, `max`) apply for the rest of the turn, or to the forked subagent. `disallowed-tools` removes tools while the skill is active. `hooks` registers session hooks when the skill is invoked. `shell` is `bash` or `powershell` for `` !`command` `` injection. `arguments` names positional arguments for `$name` substitution. `when_to_use` is extra discovery text appended to `description`.

**Cursor presentation.** `icon` and `color` style the badge when the skill is used as a Custom Mode. Colors are `default`, `green`, `cyan`, `blue`, `purple`, `magenta`, `orange`, `yellow`, `red`, and `brand`.

## What the checkers reject

The spec defines six fields:

`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`.

When Codex's bundled `quick_validate.py` must also pass, use the five-field
intersection: omit `compatibility`. The six-field set does not pass every checker.

These checkers fail the file when any other key is present:

- `skills-ref validate`
- claude.ai skill uploads, the Skills API, and `package_skill.py`
- Codex `quick_validate.py`, which allows `name`, `description`, `license`, `allowed-tools`, and `metadata` (it does not list `compatibility`)

Claude Code ignores a key it does not recognize. The Codex runtime parser reads `name`, `description`, and `metadata.short-description`, and tolerates other keys. Cursor documents the fields in the table above.

In this repo, `scripts/generate_manifests.py` reads `name` and `description` when it builds the marketplace catalogs. Other frontmatter stays in `SKILL.md` for the host that understands it.

## Built-in tools

Tool names belong to one harness. Claude's `Bash` is Cursor's `Shell`, Codex's `exec_command`, and Copilot's `bash`. `allowed-tools` has to use the names from the harness that will run the skill.

| Job | Claude Code | Cursor | Codex | Copilot CLI |
| --- | --- | --- | --- | --- |
| Read a file | `Read` | `Read` | shell, or `view_image` for images | `view` |
| Find files | `Glob` | `Glob` | shell | `glob` |
| Search contents | `Grep`, `LSP` | `Grep` | shell | `grep` |
| Edit files | `Edit`, `Write`, `NotebookEdit` | `Write` | `apply_patch` | `edit`, `create`, `apply_patch` |
| Run a command | `Bash`, `PowerShell` | `Shell` | `exec_command`, `write_stdin` | `bash`, `powershell` |
| Fetch or search the web | `WebFetch`, `WebSearch` | `WebFetch`, `WebSearch` | `web_search` | `web_fetch` |
| Ask the user | `AskUserQuestion` | documented, no tool id | `request_user_input` | `ask_user` |
| Run a subagent | `Agent` | `Task` | `spawn_agent` | `task` |
| Invoke a skill | `Skill` | — | — | `skill` |

Cursor's agent overview describes search, web, rules, read, edit, shell, browser, image generation, and questions. The identifiers above are the ones Cursor publishes for hooks and the Agent SDK. The SDK spells them in lowercase (`read`, `grep`, `shell`) and also exposes `edit`, `delete`, `ls`, and `mcp`. Its hook layer maps Claude's `Edit` onto `Write`, and it does not map Claude's `Glob`.

### Claude Code

From the [tools reference](https://code.claude.com/docs/en/tools). Permission rules can narrow a tool, as in `Bash(git status *)`, `Read(~/secrets/**)`, or `Skill(deploy *)`.

| Group | Tools |
| --- | --- |
| Files | `Read`, `Edit`, `Write`, `NotebookEdit`, `Glob`, `Grep`, `LSP` |
| Shell | `Bash`, `PowerShell`, `Monitor` |
| Web | `WebFetch`, `WebSearch` |
| User | `AskUserQuestion`, `PushNotification`, `SendUserFile`, `EndConversation` |
| Plan and tasks | `EnterPlanMode`, `ExitPlanMode`, `TodoWrite`, `TaskCreate`, `TaskGet`, `TaskList`, `TaskUpdate`, `TaskOutput`, `TaskStop` |
| Agents | `Agent`, `SendMessage`, `Workflow`, `CronCreate`, `CronDelete`, `CronList`, `ScheduleWakeup` |
| Worktrees | `EnterWorktree`, `ExitWorktree` |
| Skills | `Skill`, `ToolSearch`, `ReportFindings` |
| MCP | `ListMcpResourcesTool`, `ReadMcpResourceTool`, `WaitForMcpServers` |
| Account | `Artifact`, `RemoteTrigger`, `ShareOnboardingGuide` |

Prompting depends on permission modes and configured rules, not only the tool.
`Read`, `Grep`, and `Glob` normally do not prompt inside the working directory.
Other tools may require approval, but some read-only `Bash` commands and
preapproved `WebFetch` domains can run without a prompt. Do not rely on a
confirmation always appearing for shell, editing, or web tools.

### Cursor

| Where the name is published | Tools |
| --- | --- |
| Hook tool names | `Shell`, `Read`, `Write`, `Grep`, `Task`, `WebFetch`, `WebSearch` |
| Agent SDK allowlist | `shell`, `read`, `edit`, `delete`, `grep`, `glob`, `ls`, `task`, `mcp` |
| SDK opt-in reminders | `reminders_create`, `reminders_list`, `reminders_cancel` |

The changelog also treats `Glob` as an agent tool. Browser control, image generation, fetching rules, and asking questions are documented as agent abilities, without a tool identifier on the agent overview page.

### Codex

`codex-rs/core/src/tools/spec_plan.rs` registers a session's tools. A normal local session gets the core set. The others appear only when their feature flag is on.

| Group | Tools |
| --- | --- |
| Core | `exec_command`, `write_stdin`, `apply_patch`, `update_plan`, `view_image` |
| MCP | `list_mcp_resources`, `list_mcp_resource_templates`, `read_mcp_resource` |
| User and permissions | `request_user_input`, `request_user_input_async`, `send_message_to_user_async`, `request_permissions` |
| Context | `get_context_remaining`, `new_context`, `wait_for_environment` |
| Agents | `spawn_agent`, `send_message`, `list_agents`, `followup_task`, `interrupt_agent`, `wait_agent` |
| Other, when enabled | `exec`, `wait`, `tool_search`, `web_search`, `create_goal`, `get_goal`, `update_goal`, `list_available_plugins_to_install`, `request_plugin_install`, `multi_env_copy_file` |

Codex has no dedicated read or grep tool. Text search and file reads go through `exec_command`. `write_stdin` exists when unified exec is on, so a command can stay open and take more input.

### Copilot CLI

From the [CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference). These are the values for `--available-tools` and for a skill's `allowed-tools`.

| Group | Tools |
| --- | --- |
| Shell | `bash`, `powershell`, `list_bash`, `list_powershell`, `read_bash`, `read_powershell`, `stop_bash`, `stop_powershell`, `write_bash`, `write_powershell` |
| Files | `view`, `create`, `edit`, `apply_patch` |
| Search | `glob`, `grep` |
| Agents | `task`, `list_agents`, `read_agent`, `write_agent` |
| Other | `ask_user`, `skill`, `web_fetch` |

`grep` also answers to `rg`. Some models use `apply_patch` in place of `edit` and `create`.

Permission rules use a different vocabulary from those tool names. `--allow-tool` and `--deny-tool` take `kind` or `kind(argument)`:

| Kind | Matches |
| --- | --- |
| `read` | File or directory reads |
| `write` | Creating or modifying files |
| `shell` | Command execution. `shell(git:*)` matches `git push` and does not match `gitea` |
| `url` | `web_fetch` or shell access to a URL |
| `memory` | Storing facts in Copilot memory |
| `SERVER-NAME` | One MCP server, or `SERVER-NAME(tool)` for one of its tools |

## Sources

- [Agent Skills specification](https://agentskills.io/specification)
- [Claude Code skills](https://code.claude.com/docs/en/skills) and [built-in tools](https://code.claude.com/docs/en/tools)
- [Cursor agent skills](https://cursor.com/docs/skills), [agent tools](https://cursor.com/docs/agent/overview), [hook tool names](https://cursor.com/docs/reference/third-party-hooks), and [Agent SDK tools](https://cursor.com/docs/agent-sdk/reference/agent-config)
- [Codex skill parser](https://github.com/openai/codex/blob/main/codex-rs/skills/src/parser.rs), the bundled `skill-creator` validator, and [tool registration](https://github.com/openai/codex/blob/main/codex-rs/core/src/tools/spec_plan.rs)
- [GitHub Copilot CLI: add skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills) and the [command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference)
