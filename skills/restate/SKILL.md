---
name: restate
description: Restate the request and scope before acting, then wait for approval
disable-model-invocation: true
argument-hint: <your prompt>
---
Before doing anything, restate in 2 sentences what you think I'm asking and what you will NOT touch.

Mark anything you are inferring as "(assumed)" so it is separate from what I actually said. When a design or diagram is involved, label each part "current" or "proposed".

Read-only until I say "ok": no edits, no commands against the app, no commits. Reading files and searching are fine.

Then stop and wait.

My request: $ARGUMENTS
