# Skills stay self-contained

Each skill installs on its own (`git-janitor@killallgit`, `npx skills add`), so a procedure that several skills share, such as "has this work already landed?" or "resolve the default branch", is written out in each skill rather than extracted into an owner skill. Extracting it would add an install dependency and force every caller to keep an inline fallback for when the owner is missing, which restores the duplication. A skill depends on another only when the dependency is substantial, a script or a long procedure with its own outcomes, as `lets-finish` does on `wait-for-action` and `independent-review`.

An architecture review should not re-suggest extracting passages of a few sentences. Revisit this if a shared procedure grows to that size or its copies start to give different answers.
