# External Tracker Labels

Local markdown files use workflow statuses in frontmatter. This file only matters when the repo also mirrors work to an external tracker that needs labels or equivalent state markers.

## Local workflow statuses

### PRD statuses

| Status        | Meaning                                      |
| ------------- | -------------------------------------------- |
| `draft`       | Planning is still being shaped               |
| `approved`    | The PRD is ready to break into issue files   |
| `done`        | The initiative has been completed            |
| `superseded`  | Replaced by a newer or more accurate PRD     |

### Issue statuses

| Status          | Meaning                                      |
| --------------- | -------------------------------------------- |
| `draft`         | Not ready to execute yet                     |
| `ready`         | Ready to be picked up                        |
| `in_progress`   | Active implementation work is underway       |
| `blocked`       | Waiting on a dependency or external decision |
| `done`          | Implemented and verified                     |
| `wontfix`       | Intentionally not being actioned             |

## External label mapping

If the repo mirrors work to GitHub, GitLab, or another tracker, map any tracker-specific labels here.

| Canonical role    | Label in our tracker | Meaning                                  |
| ----------------- | -------------------- | ---------------------------------------- |
| `needs-triage`    | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`      | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent` | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human` | `ready-for-human`    | Requires human implementation            |
| `wontfix`         | `wontfix`            | Will not be actioned                     |

Edit the right-hand column to match the vocabulary your external tracker actually uses.
