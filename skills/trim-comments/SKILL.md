---
name: trim-comments
description: Run the comment trimmer by hand on the files changed in this checkout. On Claude Code the plugin also runs it on every Stop.
disable-model-invocation: true
---

# Trim comments

A Stop hook finds the comments in the files the session edited and hands them
to a reviewer on a different model. The reviewer deletes each comment whose
information the code already carries and keeps the ones that record why.

Files come from two sources, each grouped by the git repo that holds it:

- every file the transcript shows an `Edit`, `Write`, `MultiEdit` or
  `NotebookEdit` touching, in any repo
- every file changed since `HEAD` (plus untracked) in the repo the session
  started in, which catches changes made through Bash. Uncommitted work that
  predates the session is in this set too, so its comments are reviewed.

Each repo is reviewed under its own `.commentrc`, with `cwd` set to that repo.
Edits made by subagents are not in the parent transcript; the second source is
the only thing that sees them, and only in the session's own repo.

Requires `uv` and the `claude` CLI on `PATH`. Run it by hand from the checkout to review:

```bash
uv run --python 3.12 <skill-dir>/scripts/trim_comments.py
```

`--dry-run` prints the flagged comments and the reviewer prompt without calling it.
`--survey` prints, under the current `.commentrc`, the repo's most common extensions
(top 15, counted over every tracked file), the reviewable files per top-level
directory, the generated-file count and the conventional directories present.
`/setup-trim-comments` uses it to write the `.commentrc`.

## Fixed behavior

- The reviewer is `haiku`, or `sonnet` when the working agent ran on haiku, read
  from the session transcript. `TRIM_COMMENTS_MODEL` overrides it.
- The reviewer runs through `claude -p` with `Read` and `Edit` only, no MCP
  servers, no user, project or local settings, and `dontAsk` permissions. `Edit` is allowed on the flagged files by
  path and denied everywhere else. A file whose path holds `* ? [ ] { } ( ) !` is
  skipped, because those characters read as permission patterns.
- Shebangs, license headers, common lint, type and tooling directives, and PEP 723
  script blocks never reach the reviewer.
- A reviewed file is checked after the edit and restored byte for byte when it
  fails: Python must keep the same syntax tree apart from docstrings, and other
  files may only lose comment lines or comment tails.
- The check runs when the reviewer fails or times out too. An unsafe edit is rolled
  back; a deletion that passes is kept, and the file is retried on the next Stop.
- Files the reviewer changes outside the flagged set are restored, and a file it
  creates is deleted. The summary line names them.
- Everything the hook discards is copied into the git dir's
  `trim-comments-rejected` folder first.
- YAML block scalars and heredocs are protected. A comment marker inside any other
  multi-line string (a TOML `"""` string, a Go raw string, a JS template literal)
  reads as a comment and can be removed. The check cannot tell it apart.
- The hook fails open. A reviewer error, a timeout or a missing `uv` or `claude`
  shows a warning or does nothing, and never blocks the session. While the
  reviewer runs the Stop waits, for up to 5 minutes.
- Only files with a known extension are read, and only outside the default
  excludes: `node_modules`, `vendor`, `dist`, `build`, `.venv`, `venv`,
  `__pycache__`, `*.min.*`, `*_pb2.py`, `*.generated.*`.
- Files whose first five lines say `do not edit`, `@generated`, `code generated` or
  `auto-generated` are skipped.
- Styles: `python` (`tokenize` for `#`, `ast` for docstrings; a docstring that is
  a body's only statement is skipped), `hash` (`.sh .bash .zsh .yml .yaml .toml
  .rb .tf`), `slash` (`//` and `/* */` in `.js .jsx .ts .tsx .go .rs .java .c
  .cc .cpp .h .hpp .swift .kt`).

## Scope

A repo opts in by having a `.commentrc` at its root. Without one the hook does
nothing there; an empty file enables the defaults. Every key is optional:

```json
{
  "include": ["src"],
  "exclude": ["**/migrations/**", "tests"],
  "extensions": {".vue": "slash"}
}
```

- `include`: when present, only matching paths are reviewed.
- `exclude`: added to the default excludes.
- `extensions`: maps a suffix to a style, adding it or overriding a default.
- Globs match repo-relative paths: `*` stays within a directory, `**` crosses them.
  An `exclude` name without a slash (`tests`, `*.snap.py`) matches at any depth, like
  gitignore, and covers everything under a directory of that name. A path with a slash
  (`src/gen`) and every `include` entry (`src`) is anchored at the repo root; write
  `**/lib` to include `lib` at any depth.
- An invalid config shows a warning and skips the run.

## Hosts

Plugin installs register the hook on Claude Code, where it is tested. The hook
command finds the script under `${CLAUDE_PLUGIN_ROOT}` in either plugin layout, and
does nothing when the variable is unset or the script is missing, so a host that
loads the hook file without that layout stays quiet. Other hosts are untested.
`npx skills add` installs skills only, so the hook never runs there.
