# Uninstall

Take out everything factory-builder added to a repository. The install recorded what it added in `.factory/manifest.json`: generated files, host symlinks, `.gitignore` and `.worktreeinclude` lines, and the setup changes made in step 3 of the install. `scripts/uninstall_factory.py` removes the files, links, and lines. Setup changes and in-flight work need the user's call, item by item.

## 1. Name the repository

Use the path the user gave, otherwise the current git root. Done when that path is the repository you will remove the factory from.

## 2. Survey

Read `.factory/manifest.json` when it exists. From this skill's directory, run:

```bash
python3 scripts/uninstall_factory.py --dest <git-root> --dry-run
```

Then find work the uninstall would strand:

- Board entries in `.factory/board.json` whose stage is not `ready` or already integrated.
- `factory/` branches not merged into the default branch: `git branch --no-merged <default-branch> --list 'factory/*'`.
- Worktrees on `factory/` branches, and any uncommitted changes in them.

Done when you hold the dry-run list, every setup change in the manifest, and every unmerged branch, worktree, and open job.

## 3. Confirm

Show the user, in one message:

- The files, links, and lines the script will remove, including tracked files such as `.gitignore`, which will show in `git diff`.
- That `.factory/` goes too, with its board and job history. Offer `--keep-state` to keep it.
- Each setup change with its revert, and ask which to revert. An owner tool installed outside this repository may serve other repositories; name that when you ask.
- Each unmerged branch, worktree, and open job, and ask which to keep. Deleting an unmerged branch loses its commits.

Done when the user has answered for every setup change and every piece of in-flight work, and said to go ahead.

## 4. Remove

1. Remove the worktrees and branches the user chose, with the repository's worktree pattern and `git branch -D`.
2. Revert the setup changes the user chose, following each `revert` text. For a disabled plugin or skill, use [disable-plugins-and-skills.md](disable-plugins-and-skills.md) to restore the setting it names.
3. Run the script without `--dry-run`, adding `--keep-state` when the user asked for it.

Done when the script exits 0.

## 5. Verify and report

Run the dry run again. It should list only what the user chose to keep. Run `git status` and confirm the only changes are the removed lines and files.

Report what was removed, what was reverted, and what was kept on purpose, with the branches and worktrees by name. Commit only when the user asks.
