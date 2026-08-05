---
name: record
description: Record an explicitly requested agent command or validation flow as an MP4.
---

# Record

Use this skill only when the user explicitly asks to record the work, such as
“let's record this.”

1. Choose the command that demonstrates the important behavior. For multiple
   commands, put the focused flow in a temporary Bash script and record that.
2. Never include or print passwords, tokens, API keys, or other secrets.
3. Run `proofcast [--out <video.mp4>] -- <command> [args...]`.
4. Proofcast prints the command output followed by the absolute MP4 path. It
   still creates the video when the recorded command exits unsuccessfully.
5. When Proofcast finishes, say exactly `I stopped the recording.` and provide
   a clickable link to the MP4. Also report a failed command's exit status.

Proofcast captures output verbatim and does not redact secrets.
