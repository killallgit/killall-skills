# Quickstart: validate the slimmed agent-setup skill

## Prerequisites

- `git` and `python3` (3.9 or later) on `PATH`.
- For the spikes: Claude Code, Codex, and Cursor installed and signed in.

## 1. Run the eval

```bash
cd skills/agent-setup
python3 evals/run.py
```

Expected: one `PASS <case>` line per case in `evals/evals.json`, exit 0. Cases cover:

- all hosts, single host, and two-host installs (contracts/render-cli.md, Outputs per host);
- agent metadata parity (data-model.md, Agent definition);
- `AGENTS.md` and `CLAUDE.md` unchanged after install;
- refusal on a foreign agent file, a foreign `agent` setting, and a foreign
  `developer_instructions` key;
- upgrade from a repository set up by the previous version: old blocks and `orchestrate` skills
  removed;
- remove: every marked file, key, and block gone; foreign content untouched;
- the edge cases in spec.md.

## 2. Check parity against the previous version, once

```bash
python3 evals/compare_previous.py <git-ref-of-previous-version>
```

Expected: identical agent metadata for builder, reviewer, and hall-monitor on every host; the only
file-set differences are the ones listed in contracts/render-cli.md.

## 3. Check the text

```bash
grep -rniE 'serena|gstack|mattpocock|spec kit|npx' skills/agent-setup && echo FAIL || echo PASS
wc -w skills/agent-setup/SKILL.md skills/agent-setup/templates/*
```

Expected: `PASS`; total words at most 2,146 (60% of the 3,577 baseline, SC-001).

## 4. Spikes S1 to S3: does the session start as the orchestrator?

Set up a scratch fixture repository with the renderer, then on each host:

| Spike | Start | Ask | Pass when |
| --- | --- | --- | --- |
| S1 Claude Code | `claude` in the fixture | "What is your role, and what do you do with a spec that has two independent parts?" | Answers as the orchestrator; starts two builders; built-in tool use still works |
| S2 Codex | `codex` in the trusted fixture | same | Answers as the orchestrator; a spawned builder does not claim the orchestrator role; builder writes succeed under its own sandbox |
| S3 Cursor | Cursor agent in the fixture | same | Answers as the orchestrator; a spawned builder does not claim the orchestrator role |

Record each result in the PR description. A failed spike switches that host to report-only
(research.md, R1).
