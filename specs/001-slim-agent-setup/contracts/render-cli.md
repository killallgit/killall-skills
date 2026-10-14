# Contract: renderer command line

`python3 scripts/render_agents.py`, run from `skills/agent-setup/`. Python 3.9 or later, standard
library only.

## Flags

| Flag | Required | Meaning | Change |
| --- | --- | --- | --- |
| `--dest <path>` | yes | Target git checkout | unchanged |
| `--vars <file>` | unless `--remove` | JSON template values, see data-model.md | unchanged; three keys removed |
| `--hosts <list>` | no | Comma-separated subset of `claude,codex,cursor`; default all | unchanged |
| `--force` | no | Replace files and settings agent-setup did not write | now also covers start-up settings |
| `--remove` | no | Remove everything any version wrote | now also removes start-up settings |
| `--instructions <file>` | no | Instruction file for the block | **removed** (FR-003) |

## Exit behavior

| Condition | Exit | Writes anything |
| --- | --- | --- |
| `--dest` is not a git checkout | non-zero | no |
| `--vars` missing without `--remove` | non-zero | no |
| Unknown or empty host list | non-zero | no |
| A required value missing or empty | non-zero, names the field | no |
| A value contains `'''` | non-zero | no |
| A target file or start-up setting not written by agent-setup, without `--force` | non-zero, lists each path | no |
| Success | 0 | yes; one `wrote <path>` or `removed <path>` line per change |

A run that fails writes nothing: all checks happen before the first write.

## Outputs per host on install

| Host | Files |
| --- | --- |
| claude | `.claude/agents/{builder,reviewer,hall-monitor,orchestrator}.md`; `agent` key in `.claude/settings.json` |
| codex | `.codex/agents/{builder,reviewer,hall-monitor}.toml`; marker block in `.codex/config.toml` |
| cursor | `.cursor/agents/{builder,reviewer,hall-monitor}.md`; `.cursor/rules/orchestrator.mdc` |

Install also clears legacy artifacts (data-model.md, Legacy artifacts) on every host, chosen or
not, when they carry the marker. Rows for hosts whose spike failed drop their start-up setting.
