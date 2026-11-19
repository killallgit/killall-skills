---
name: setup-trim-comments
description: Define a project's .commentrc for trim-comments by surveying the repo and asking which directories and extensions to cover.
disable-model-invocation: true
---

# Set up trim-comments

Write the project's `.commentrc`: the file that opts a repo into the
`trim-comments` hook and sets its `include`, `exclude` and `extensions`. Work
from the repo root, which must be a git repository. When a `caveman` skill is
available in this session, invoke it first.

The survey is the `trim-comments` script. It sits next to this skill, in
`../trim-comments/scripts/trim_comments.py`, and needs `trim-comments` installed.
When that path is missing, stop and tell the user to install `trim-comments`
beside this skill.

## 1. Survey

Run `uv run --python 3.12 <skill-dir>/../trim-comments/scripts/trim_comments.py --survey`
from the repo root. When `.commentrc` exists, read it too: its keys are the
starting answers, and the survey already applies them.

Done when you can say which directories hold the project's own code, which hold
vendored, fixture or example code, and which suffixes are `unsupported`. The
extension counts cover every tracked file, and the list stops at the top 15.

## 2. Decide

Ask one question per decision the survey leaves open, with a recommended option
first. Skip a decision the survey settles.

- **`include`**: the top-level directories to cover, such as `src`. Recommend the
  ones holding the project's own code. Omit `include` when the code spans the whole tree.
- **`exclude`**: the conventional directories present (`tests`, `fixtures`,
  `migrations`, `examples`), tool and agent config directories (`.claude`,
  `.agents`, `.beads`), and anything else vendored. Tests are the user's call: an
  agent writes restating comments there too.
- **`extensions`**: each `unsupported` suffix with many files, mapped to `hash`
  (`#` comments) or `slash` (`//` and `/* */`). Leave out suffixes whose comment
  syntax is neither.

Generated files with a `do not edit` header are skipped already; leave them out
of `exclude`.

## 3. Write

Write `.commentrc` at the repo root as JSON. A new file holds only the keys that
differ from the defaults, and `{}` enables the defaults. An existing file keeps
every key this run did not change, even one equal to a default. In `exclude`, write a directory as a
plain name (`tests`) to match it at any depth, or as a path (`src/gen`) to anchor it at
the repo root. In `include`, plain names are anchored at the repo root (`src`); use
`**/lib` for any depth. A glob such as `**/migrations/**` works in both, with `*`
staying within a directory and `**` crossing them.

## 4. Verify

Run the survey again. Done when it prints no `bad config`, the per-directory
counts match what the user chose, and each excluded conventional directory has left
the `conventional directories present` list. Fix the file and rerun until they do.

End with the file's contents and one line: commit `.commentrc` so teammates and
worktrees inherit it.
