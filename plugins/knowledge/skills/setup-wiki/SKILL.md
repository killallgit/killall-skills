---
name: setup-wiki
description: Create or adopt a shared cross-project LLM wiki with immutable sources, compiled Markdown, a typed claim graph, lightweight ontology, validation, and optional lifecycle hooks. Use when the user asks for `/setup-wiki`, a Karpathy-style wiki, a project knowledge graph, or durable knowledge spanning multiple repositories.
---

# Setup Wiki

Build one knowledge vault for a domain that spans several projects. The normal
location is `<projects-root>/<name>-wiki`, beside the repositories it covers.

## Process

1. Inspect before asking:
   - current Git root and its parent;
   - nearby Git repositories at the same projects root;
   - existing `.wiki.json` pointers and `*-wiki/wiki.json` vaults;
   - agent instructions, ignored paths, and likely sensitive files.
2. Follow [INTERVIEW.md](./INTERVIEW.md). Ask one decision at a time and infer
   only what the filesystem makes unambiguous.
3. Present one setup summary: vault path, purpose, projects, exclusions,
   source ownership, audience, sensitivity, freshness, ontology seeds,
   retrieval, Git policy, and requested hooks.
4. Obtain confirmation before creating the vault, writing project pointers, or
   changing user-level host configuration.
5. Run the companion scaffold with absolute paths:

```bash
python3 <skill-dir>/scripts/setup-wiki.py \
  --vault <projects-root>/<name>-wiki \
  --name <name> \
  --purpose "<purpose>" \
  --project <absolute-project-path> \
  --exclude "<glob>" \
  --option audience=<value> \
  --option sensitivity=<value> \
  --option git_policy=<value> \
  --option retrieval=<value>
```

Repeat `--project`, `--exclude`, and `--option` as needed. Do not initialize a
Git repository or create a remote unless the confirmed Git policy requests it.

6. Inspect created and preserved files. Existing content is user-owned; merge
   intentional contract improvements rather than replacing it.
7. Run `<vault>/scripts/wiki-check.py <vault>`.
8. If hooks were approved, follow [HOOKS.md](./HOOKS.md). Hook registration is
   a separate side effect after the vault validates.
9. Report created, preserved, configured, skipped, and manual follow-up items.

The scaffold requires only Python 3. Obsidian, qmd, embeddings, RDF, and graph
databases are optional projections.
