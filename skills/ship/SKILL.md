---
name: ship
description: Open PR, wait for CodeRabbit, fix findings, merge, sync main, clean up. Use when the user says "ship it", "ship this", or invokes `/ship`.
---

1. Push the branch and run `gh pr create --fill`.
2. Invoke the wait-for-action skill with `--coderabbit`. If rate-limited, stop and ask the user.
3. Fix every finding, push, and repeat step 2 until clean.
4. Run `gh pr merge --squash --delete-branch`, then `git checkout main && git pull`.
5. Invoke the git-janitor skill.
6. Report: PR number, findings fixed.
