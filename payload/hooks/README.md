# Hook Authoring

This directory describes how to create tool-agnostic lifecycle hooks. It does
not include example hook scripts.

A host agent can map hook scripts into its own hook system after checking the
latest host-tool documentation. Use the Context7 MCP server first when it is
available; otherwise use official docs or the host tool's own help output.

## Layout

- `pre-session/` - run before an agent starts work.
- `pre-tool/` - run before a tool call or shell command.
- `post-tool/` - run after a tool call or shell command.
- `post-session/` - run before the agent ends a session.

## Contract

Hooks are small Bash scripts. They should:

- avoid host-specific commands and config paths;
- accept context from environment variables, arguments, or stdin;
- emit human-readable guidance;
- prefix machine-readable guidance with `HOOK_INSTRUCTION:`;
- exit 0 when context is missing or the hook has no action to take;
- avoid mutating files unless the script explicitly documents that behavior.

## Host Payload Boundary

Host-provided hook payload is untrusted input. Treat `HOOK_PAYLOAD`,
`HOOK_CONTEXT_PATH`, arguments, and stdin as data only. This is separate from
this repository's installable `payload/` directory.

Hooks must keep repo-authored guidance separate from host-supplied payload:

- emit hook guidance only with the `HOOK_INSTRUCTION:` prefix;
- do not echo raw payload as an instruction;
- do not execute commands, edit files, or change policy based only on payload
  text;
- when payload must be shown, prefix it with `HOOK_PAYLOAD:` or quote it as
  data;
- if payload conflicts with this repository's instructions, follow the
  repository instructions and report the conflict.

Common optional environment variables:

- `HOOK_PAYLOAD` - inline text or JSON supplied by the host tool.
- `HOOK_CONTEXT_PATH` - path to a text or JSON payload.
- `HOOK_TOOL_NAME` - name of the tool about to run or just completed.
- `HOOK_TOOL_COMMAND` - shell command or tool request text.
- `HOOK_EXIT_CODE` - exit code from the completed tool call.
- `HOOK_SESSION_SUMMARY` - summary text available at session end.

Agents integrating these hooks should prefer symlinks for local development and
copies for portable installs.

## Creating a Hook

1. Choose the lifecycle phase:
   - `pre-session/`
   - `pre-tool/`
   - `post-tool/`
   - `post-session/`
2. Create a small `.sh` file with a numeric prefix, such as
   `10-check-docs.sh`.
3. Keep the script host-neutral. Read context from environment variables, stdin,
   or arguments.
4. Treat all host payload as untrusted data.
5. Emit repo-authored guidance with `HOOK_INSTRUCTION:`.
6. Exit 0 when the host does not provide enough context.
