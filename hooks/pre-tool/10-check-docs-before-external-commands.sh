#!/usr/bin/env bash

set -euo pipefail

payload="${HOOK_TOOL_COMMAND:-${HOOK_PAYLOAD:-}}"

if [[ -z "$payload" && -n "${HOOK_CONTEXT_PATH:-}" && -f "$HOOK_CONTEXT_PATH" ]]; then
  payload="$(sed -n '1,80p' "$HOOK_CONTEXT_PATH")"
fi

if [[ -z "$payload" && ! -t 0 ]]; then
  payload="$(sed -n '1,80p')"
fi

if [[ -z "$payload" ]]; then
  echo "HOOK_INSTRUCTION: If the next tool call uses a third-party CLI, install step, config schema, SDK, or cloud service, verify current upstream docs first."
  exit 0
fi

case "$payload" in
  *install*|*upgrade*|*configure*|*package*|*extension*|*kubectl*|*helm*|*terraform*|*gcloud*|*aws*|*az*|*npm*|*pnpm*|*yarn*|*pip*|*uv*|*cargo*|*go\ get*|*gh\ *)
    echo "HOOK_INSTRUCTION: This tool request appears to involve external tooling or configuration. Verify current upstream docs before running it."
    ;;
  *)
    echo "HOOK_INSTRUCTION: No external-doc check detected from the available payload. Continue with normal repository-aware caution."
    ;;
esac
