# killall-skills

General-purpose engineering skills for Codex, Claude Code, and Cursor. Skills are authored once under `skills/`, then packaged as Codex and Claude plugins or exported as Cursor project rules.

## Install

### Codex

Marketplace install:

```bash
codex plugin marketplace add killallgit/killall-skills
```

Then reopen Codex, open the Plugins UI, and install `killall-skills` from the `killallgit` marketplace.

Local checkout / development:

```bash
codex plugin marketplace add /absolute/path/to/killall-skills
```

Then reopen Codex, open the Plugins UI, and install `killall-skills` from the `killallgit` marketplace backed by your local checkout.
Codex reads the in-repo plugin from `./plugins/killall-skills`. That directory points back at the root source files, so local edits do not need a sync or copy step; restart Codex or reinstall the plugin if the current session has stale plugin state.

### Claude Code

Marketplace install:

```bash
claude plugin marketplace add killallgit/killall-skills
claude plugin install killall-skills@killallgit
```

Local checkout install:

```bash
claude plugin marketplace add /absolute/path/to/killall-skills
claude plugin install killall-skills@killallgit
```

Session-only local development:

```bash
claude --plugin-dir /absolute/path/to/killall-skills
```

### Cursor

Marketplace install: not supported. Cursor's official extension surface is project rules in `.cursor/rules` or a root `AGENTS.md`.

Local checkout / development:

```bash
bash scripts/export-cursor-rules.sh /path/to/target-repo
```

This copies the source skills into `/path/to/target-repo/.cursor/killall-skills/skills/` and generates agent-requested rule files in `/path/to/target-repo/.cursor/rules/`. Use the generated rules when you want the full skill pack; use a root `AGENTS.md` only for lightweight global repo instructions.

## Validate

Smoke-test the install surfaces and exported Cursor rules:

```bash
bash scripts/smoke-test-install.sh
```

If Claude Code is installed locally, you can also run the native validator directly:

```bash
claude plugin validate .
```

## License

MIT
