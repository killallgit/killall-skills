# killall-skills

General-purpose Claude Code and Codex skills for software engineering. Language and framework agnostic.

## Install

### Codex

Add the marketplace:

```bash
codex plugin marketplace add killallgit/killall-skills
```

For local development:

```bash
codex plugin marketplace add ~/Code/killallgit/killall-skills
```

Then restart Codex, open `/plugins`, and install `killall-skills` from the killallgit marketplace.

### Claude Code

```
/plugin marketplace add killallgit/killall-skills
/plugin install killall-skills@killallgit
/reload-plugins
```

## Develop locally

```bash
claude --plugin-dir /path/to/killall-skills
```

For Codex local development, add the local marketplace path shown above and reinstall from `/plugins`.

## License

MIT
