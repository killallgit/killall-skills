---
name: handoff
description: Produce a self-contained handoff prompt that lets a fresh-context agent pick up the current work without re-discovering it. Use when the user wants a "handoff", "handoff prompt", to "pass this off", to "continue in a new session", or otherwise needs to transfer in-flight work to another agent.
---

# Handoff

Synthesize the current conversation into a single prompt the next agent can paste in cold and immediately be productive. Do NOT interview the user — write from what you already know. If a critical fact is missing, ask one targeted question, then write.

The output is the prompt itself. Print it in a single fenced block so it copies cleanly. No preamble, no trailing summary.

## What a good handoff prompt contains

Brief the next agent like a smart colleague who walked into the room. They have not seen this conversation. Cover, in this order:

1. **Goal** — one sentence. What done looks like.
2. **Why it matters** — one sentence of motivation, only if non-obvious.
3. **State** — what's already done, what's in progress, what's untouched. Use file paths and line numbers. Name branch / worktree / PR if relevant.
4. **Key decisions made** — choices already locked in, with the reason. Prevents re-litigating.
5. **Dead ends / ruled out** — approaches tried that didn't work, so the next agent doesn't repeat them.
6. **Gotchas** — non-obvious constraints, hidden coupling, quirks of the env, flaky tests, auth steps.
7. **Next step** — the single concrete action to take first. Not a plan; a starting move.
8. **Success check** — how the next agent will know the work is done (test command, manual check, expected output).
9. **Open questions** — anything blocked on the user. Mark clearly.

## Rules

- **Self-contained.** No "as we discussed" or "the file we looked at". Name the file.
- **Concrete over abstract.** `src/auth/middleware.ts:42` beats "the auth code".
- **Skip what doesn't apply.** No section needs to exist if it has nothing in it. Better short than padded.
- **No invented context.** If you don't know it, omit it or mark it as an open question. Never fabricate.
- **Match scope.** A 10-minute task gets a 10-line handoff. A multi-day project gets more — but still no fluff.
- **Project vocabulary.** Use the domain glossary terms the current project uses. Don't rename concepts.

## Process

1. Skim the conversation: what was the user asking for, what got done, what's the next move.
2. Check git state if relevant (`git status`, `git diff --stat`, branch name) so file lists are accurate.
3. Draft the prompt against the structure above. Cut anything that isn't load-bearing.
4. Print the prompt in a single fenced ` ```text ` block. Nothing else in your response except the block.

## Template

```text
# Handoff: <one-line goal>

## Goal
<one sentence>

## State
- Done: <bullets with file:line>
- In progress: <bullets with file:line>
- Branch / worktree / PR: <if any>

## Decisions locked in
- <decision> — <why>

## Ruled out
- <approach> — <why it didn't work>

## Gotchas
- <constraint, quirk, or trap>

## Next step
<one concrete action>

## Success check
<command to run / behavior to verify>

## Open questions for the user
- <question>
```

Drop any section that would be empty.
