---
name: ship
description: Open PR, wait for CodeRabbit, fix findings, merge, sync main, clean up
---

1. Push the branch and run `gh pr create --fill`.
2. Run `wait-for-action --coderabbit`. If rate-limited, spawn a local review agent instead.
3. Fix every finding, push, and repeat step 2 until clean.
4. Run `gh pr merge --squash --delete-branch`, then `git checkout main && git pull`.
5. Run /git-janitor.
6. Report: PR number, findings fixed.
