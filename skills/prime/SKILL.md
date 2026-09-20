---
name: prime
description: Map the project before work starts as a terse list — layout, entrypoints and flow, core patterns, load-bearing libraries, useful scripts and commands, related repos — from one survey command and a few capped reads, adding well under fifty thousand tokens. Ends at the map.
disable-model-invocation: true
---

# Prime

Build a map of the project while context is cheap, so the work that follows
opens the right files instead of exploring. The map records what is actually
there: the code is the source of truth, and every README or `CLAUDE.md` is a
set of claims to check against it.

Prime runs inside the session that will do the work, so every token it spends
is one the task cannot. The whole pass is one survey command, at most three
capped reads, the docs written for agents, and the map — well under fifty
thousand tokens added. The survey does the inventory and the counting; your
job is the judgment on top of it.

When a `caveman` skill is available in this session, invoke it (`/caveman`)
before anything else: everything you say from here on, the map included, is
output tokens, and caveman drops the filler while keeping paths, names,
commands, and error strings exact.

## 1 — Survey

```bash
python3 <this skill's directory>/scripts/survey.py <project path>
```

Read-only: standard library only, shells out to `git` listing commands and
`du`, writes nothing — run it, don't audit it. The path defaults to the
current directory; point it at the repository root, or at one package of a
monorepo when the work is scoped to that package. `--full` lifts the list caps
when a capped line cuts off something you need.

It prints about a hundred lines:

- **git state** — branch, commits, uncommitted and untracked work, drift from
  upstream, ignored artifacts, nested worktrees (excluded from its counts;
  exclude them from your greps too: `grep --exclude-dir=worktrees`).
- **size and tier**, languages, layout with file counts.
- **commands** declared in manifests with their runner (`task test`, `make
  build`), commands mentioned in docs, and **scripts** with their first doc
  line and who calls them.
- **dependencies** as declared, then **libraries in use** counted by importing
  file, with test-only libraries, declared-but-never-imported ones, and
  imports nothing declares.
- **internal hubs** — the modules most imported by the rest of the project —
  and **stdlib signals** (sqlite3, subprocess, asyncio, …) with the files
  using them.
- **patterns** — decorators, base classes, idioms, typing discipline, test
  idioms — each counted by file, naming every file when there are three or
  fewer and the heaviest user otherwise.
- **entrypoints**, then an **outline** (line-numbered top-level definitions
  and wiring calls; a tiny file shows its statements) of the main ones and of
  the top hubs.
- tests, CI commands, docs, recent activity, sibling repositories ranked by
  evidence in both directions.

Absences are stated (`commands: none declared`). Every line is a lookup you
would otherwise spend a tool call on: treat it as read.

`tier: empty` is a bare repository: report the survey in two or three lines
and stop. `scaffold signals` (no commits, a few hundred lines) means the map is
the survey's facts plus the entrypoint's shape from its outline — ten to
twenty lines, no code reads; `CLAUDE.md` and `AGENTS.md` are still worth their
few lines. Otherwise continue.

## 2 — Read, within budget

At most three reads, each capped — `sed -n '1,120p'`, or `grep -n` for one
mechanism — because a 300-line file costs more context than the whole map is
worth. Spend them where the survey stops:

1. **The wiring.** The main entrypoint around the lines its outline names:
   what startup builds and in what order (config, database, clients,
   middleware, background jobs) and the first hop from a request or command
   into the business logic.
2. **The top hub.** The shape of the core abstraction everything imports —
   what it exposes, what it assumes.
3. **One test file.** How tests are written — fixtures, factories, mocks, a
   real database. The survey's test idioms name the heaviest one.

Then read `CLAUDE.md` and `AGENTS.md` when the survey lists them — they are
written for you and usually short. For README and architecture docs, read the
headings and the sections on layout or commands only. Compare each claim with
what the survey counted and what you read: a disagreement (a command that no
longer exists, a rule the code breaks, a layer the code bypasses) is worth a
line in the map; agreement is not. Where a doc explains *why* something is
built the way it is, keep the reason — the code cannot show you that.

When the reads are spent, the reading is over: write from what you have and
mark what you inferred. Subagents are not part of this pass; each carries its
own system prompt and costs more than the whole map.

## 3 — Write the map

A list, not a report. One fact per line — a line joining two facts with `|`
or `;` is two lines — under a hundred characters where a path allows, names
and paths over descriptions. The reader is the next task, scanning for where
to go, and a paragraph costs it the same tokens it cost you. No sentences
about how you found something. Forty to fifty lines. Drop an empty section,
except Related projects, which says "none" when the survey checked and found
nothing.

One write, to wherever the task asked; when it named no file, the map is your
reply. Also write it to `<scratchpad>/prime.md` when this session has a
scratchpad, so it survives compaction.

```markdown
# <project name>
- <what it is>: <stack>, <size>, <activity>
- checkout: <branch>, <uncommitted work>, <drift from upstream>

## Layout
- <dir>/ — <what lives there>, <how it is split>; <where the convention breaks>
- tests: <where>, <unit vs integration split>

## Entrypoints and flow
- <entrypoint> → <what startup builds, in order> (<path>:<line>)
- <request | command | event> → <handler> → <logic> → <database | HTTP | queue> (<paths>)
- auth: <where enforced>; side effects: <where>

## Core patterns
- DI: <mechanism> (<path>)
- config: <how loaded and validated> (<path>)
- errors: <how represented at the boundary> (<path>)
- data: <ORM | raw SQL>, <migration tool> (<path>)
- <sync | async>; typing: <discipline>
- tests: <framework>, <fixtures | factories | mocks | real database> (<path>)
- distinctive: <what a newcomer would not guess from the framework> (<path>)

## Libraries
- <library> (<n> files) — <what for> (<where>)
- declared, never imported: <names>

## Scripts and commands
- test: `<command>` (needs <database | env var | token>)
- lint: `<command>`
- typecheck: `<command>`
- build: `<command>`; run: `<command>`
- <scripts/name> — <what it does> (<who calls it>)

## Related projects
- <repo> — <dependency | client | deployer | docs>, <evidence>

## Watch out
- <doc claim that disagrees with the code>
- <stale command | test that needs a service | dead directory | checkout behind upstream>
```

Each placeholder is a slot, not a sentence. `- DI: FastAPI Depends for auth,
module singletons otherwise (config/settings.py)` is the density; repeat a
slot's line when it has more than one fact. A line the survey counted or you
read stands bare; a line you inferred ends in `(inferred)`.

## Rules

- Every line is something you read or the survey counted, or it carries
  `(inferred)`.
- Map, don't review: say where the organization breaks down because new code
  has to live somewhere; leave the refactoring opinions out.
- End at the map. Priming precedes work; wait for the task even when the next
  step looks obvious.
