#!/usr/bin/env bash
cmd=$(jq -r '.tool_input.command')
[[ "$cmd" != *"gh pr merge"* ]] && exit 0
if ! gh pr checks --json name,state | jq -e '.[] | select(.name|test("CodeRabbit";"i")) | select(.state=="SUCCESS")' >/dev/null; then
  echo 'Blocked: CodeRabbit review not complete' >&2; exit 2
fi
