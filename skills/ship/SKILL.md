---
name: ship
description: Open PR, get it independently reviewed and fixed, merge, sync main, clean up. Use when the user says "ship it", "ship this", or invokes `/ship`.
---

1. Invoke the independent-review skill and let it finish. It opens the PR, waits for the repo's CI reviewers or runs a local review agent, and resolves every finding. If it leaves findings open, stop and ask the user.
2. Run `gh pr merge --squash --delete-branch`, then `git checkout main && git pull`.
3. Invoke the git-janitor skill.
4. Report: PR number, who reviewed, findings fixed.
