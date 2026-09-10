---
name: catch-up
description: Rebuild a human's lost context on the work in flight — a short state of play, the decisions that stuck and why, live issues/PRs/tickets, plain-language explanations of whatever is load-bearing, and the single clear next step. Use when the user says "catch me up", "where were we", "what's the state of this", or invokes `/catch-up` after time away.
---

# Catch Up

Time has passed and the user has lost the thread — an interrupted session, a
weekend, a compaction. Rebuild it for them.

They are asking precisely because re-reading the whole chain is expensive. Do
that reading yourself and hand back the conclusion. A summary that requires
scrolling back to interpret has failed.

**Write for a human who has forgotten, not for an agent resuming.** State what
is true now. Do not narrate how you got here, replay tool calls, or list every
file touched.

## Gather

Read before writing. Cheap, and wrong summaries come from skipping it.

1. **The conversation.** Which decisions were actually settled, and why each one
   went the way it did. A position the user reversed is not a decision — record
   where it landed, not the journey. Note anything you asked that never got
   answered.
2. **The working tree.** `git status`, `git log --oneline @{u}..` and
   `origin/main..HEAD`, plus the uncommitted diff. Separate what is committed
   from what is pushed from what is merged — these drift apart while someone is
   away, and the user's memory will be of whichever one they last saw.
3. **What moved without them.** Has `main` advanced? Did a PR get merged,
   reviewed, or go red? This is the part they cannot reconstruct from memory at
   all, so it earns its place even when the answer is small.
4. **Trackers — only the ones this repo actually uses.** Check for wiring before
   querying, and skip any that is absent:
   - GitHub: `gh pr list`, `gh issue list`, `gh pr checks <n>` when a PR is open.
   - Jira or another external tracker: query it only if the repo or the session
     already established a project key. Never guess one.

   Never invent a ticket, a number, or a status. Silence is correct when nothing
   is wired up.

## Write

Use these sections in this order. **Drop any section that is empty** — never
emit a heading with "none" or "n/a" under it.

### Where we are

Two to four sentences. What is being built, and what state it is in right now.
Written so it makes sense cold, without the sections below.

### Decisions

The ones that constrain what happens next, each with its reason in the same
line. Omit decisions that no longer bind anything.

### Open items

Only if issues, PRs, or tickets exist. One line each, with live status:

| Ref | What | Status |
| --- | --- | --- |
| #12 | <one phrase> | open, CI red |

### Concepts

ELI5, and only for what is **load-bearing for the next step** — a term, tool, or
mechanism the user must hold to judge what you do next. Two or three sentences
each, no jargon defended by more jargon.

Skip this section by default. Most catch-ups need it zero times. Explaining
something the user already understands is noise, and reads as padding.

### Next

**One clear next step**, stated as an action. Anything else queued goes
underneath it, ordered, so the single next thing stays unambiguous.

If the next step is blocked, say what it is blocked on and who can unblock it —
a failing test, an unanswered question, someone else's review.

## Rules

- **One screen.** If it does not fit, you are including history instead of state.
- **No false precision.** If you are unsure whether something landed, check it.
  If you cannot check it, say so plainly rather than smoothing it over.
- **Do not re-litigate.** Settled decisions are reported, not reopened, even
  where you would have chosen differently.
- **Do not start work.** This skill ends at the summary. Wait for the user to
  pick the next step, even when it is obvious.
