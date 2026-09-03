# Changelog

## Unreleased

### ⚠ BREAKING CHANGES

* Plugin distribution is removed. The Claude Code and Codex plugin
  marketplaces, the per-domain plugin manifests, and `install.sh` are gone, and
  the release-please version wiring with them. Skills now live in a
  `skills/<domain>/<name>/` catalog and install through the cross-agent
  `skills` CLI:

  ```bash
  npx skills@latest add killallgit/killall-skills --skill '*' -a claude-code -g -y
  ```

  If you installed a domain as a plugin, uninstall it
  (`claude plugin uninstall <domain>@killallgit`) before reinstalling.

* Subagents moved from each plugin to a top-level `agents/`. The `skills` CLI
  does not install subagents; copy them into your host's agent directory.

## [0.6.1](https://github.com/killallgit/killall-skills/compare/killall-skills--v0.6.0...killall-skills--v0.6.1) (2026-08-24)


### Bug Fixes

* keep a failed install from removing a working plugin ([0b3672d](https://github.com/killallgit/killall-skills/commit/0b3672d69b468ebc9f21b2ce8b8e24491e57c695))

## [0.6.0](https://github.com/killallgit/killall-skills/compare/killall-skills--v0.5.0...killall-skills--v0.6.0) (2026-08-21)


### Features

* add commenator comment-audit agent ([4521d99](https://github.com/killallgit/killall-skills/commit/4521d99602c367a0d65802b7c807864d7be33f7a))

## 0.5.0 (2026-08-05)

### Features

* distribute planning, engineering, architecture, knowledge, and experimental as independent plugins
* install selected domain plugins or individual cross-agent skills
* consolidate extension authoring and Git worktree maintenance workflows

### Removals

* remove redundant grilling, setup, and prompt-shortcut skills

## 0.4.0 (2026-07-30)

### Features

* add a generic cross-project wiki with guided setup and runtime workflows
* add provenance-aware ontology claims and graph validation
* add reversible Claude Code and Codex lifecycle hooks
* add an installer for refreshing the plugin across supported hosts

### Bug Fixes

* enforce source and page graph identity in wiki validation

## 0.3.1 (2026-07-20)


### Bug Fixes

* set up automated release tagging for Claude and Codex plugins
