# agent-setup evals

Run every case: `python3 evals/run.py` from `skills/agent-setup/`. Run some: `python3 evals/run.py <id> <id>`.
Compare agent metadata with an earlier version: `python3 evals/compare_previous.py <git-ref>`.

Each case in `evals.json` builds a fresh git repository, runs `scripts/render_agents.py --dest <repo>`
with `args`, and checks the result. Fields:

| Field | Meaning |
| --- | --- |
| `id` | Case name, printed as `PASS <id>` or `FAIL <id>` |
| `files` | Files committed into the fixture before anything runs |
| `previous` | `{"ref": "<git-ref>", "hosts": "..."}`: set the fixture up with agent-setup as it was at that ref |
| `setup` | Renderer argument lists run before the snapshot, such as an earlier install |
| `files_after_setup` | Files written after `setup` and before the snapshot |
| `vars` | Overrides merged onto `fixtures/vars.json`; `{vars}` in `args` and `setup` expands to the result |
| `args` | Renderer arguments under test; `{fixtures}` expands to `evals/fixtures` |
| `expect_exit` | Exit code, or `"nonzero"`; default 0 |
| `expect_changes` | Exact `added`, `removed`, or `modified` path lists, relative to the snapshot |
| `expect_files`, `expect_absent`, `expect_unchanged` | Paths that must exist, must not exist, or must keep their content |
| `expect_metadata` | `{path: {key: value}}` from frontmatter, single-line TOML keys, or JSON; `null` means the key must be absent |
| `expect_startswith`, `expect_endswith` | `{path: text}` |
| `expect_toml` | Paths that must parse as TOML (checked on Python 3.11+) |
| `expect_no_match` | Regexes no added or modified file may match |
| `expect_output` | Strings the renderer's output must contain, such as a refused path or a missing field name |
| `text_budget` | `{max_words, max_renderer_lines, forbidden}`: checks the skill's own text instead of a fixture |
