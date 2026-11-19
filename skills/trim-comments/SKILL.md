---
name: trim-comments
description: Run the comment trimmer by hand on the files changed in this checkout. Installing the plugin also runs it on every Stop.
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
  started in, which catches changes made through Bash

Each repo is reviewed under its own `.commentrc`, with `cwd` set to that repo.
Edits made by subagents are not in the parent transcript; the second source is
the only thing that sees them, and only in the session's own repo.

Run it by hand:

```bash
uv run --python 3.12 scripts/trim_comments.py
```

`--dry-run` prints the flagged comments and the reviewer prompt without calling it.

## Fixed behavior

- The reviewer is `haiku`, or `sonnet` when the working agent ran on haiku, read
  from the session transcript. `TRIM_COMMENTS_MODEL` overrides it.
- The reviewer gets `Read` and `Edit` only, through `claude -p`.
- Shebangs, license headers, lint and type directives, and PEP 723 script
  blocks never reach the reviewer.
- A file is reviewed once per content: the post-review hash lives in
  `<git-dir>/trim-comments.json`, so an unchanged dirty file costs no second call.
- The hook fails open. A reviewer that errors or times out shows a warning and
  never blocks the session.
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
  "include": ["src/**"],
  "exclude": ["**/migrations/**", "tests/**"],
  "extensions": {".vue": "slash"}
}
```

- `include`: when present, only matching paths are reviewed.
- `exclude`: added to the default excludes.
- `extensions`: maps a suffix to a style, adding it or overriding a default.
- Globs match repo-relative paths: `*` stays within a directory, `**` crosses them.
- An invalid config shows a warning and skips the run.

Plugin installs register the hook. `npx skills add` installs skills only, so
the hook never runs there.
