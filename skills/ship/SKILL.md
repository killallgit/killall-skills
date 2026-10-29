---
name: ship
description: Open PR, wait for CodeRabbit, fix findings, merge, sync main, clean up. Use when the user says "ship it", "ship this", or invokes `/ship`.
---

1. Push the branch and run `gh pr create --fill`.
2. Invoke the wait-for-action skill with `--coderabbit`. It restarts a skipped or rate-limited review itself. If it exits 3 (error, including unreadable findings) or 4 (not reviewed), stop and ask the user.
3. Fix every finding, resolve its thread (ids are in `findings.json`), push, and repeat step 2 until clean. `findings.json` lists inline threads only: also read the CodeRabbit review bodies, as the wait-for-action skill describes, for findings outside the diff.
4. Run `gh pr merge --squash --delete-branch`, then `git checkout main && git pull`.
5. Invoke the git-janitor skill.
6. Report: PR number, findings fixed.
