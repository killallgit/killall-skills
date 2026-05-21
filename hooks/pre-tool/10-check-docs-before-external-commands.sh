#!/usr/bin/env bash

set -euo pipefail

read_context() {
  if [[ -n "${HOOK_TOOL_COMMAND:-}" ]]; then
    printf '%s' "$HOOK_TOOL_COMMAND"
    return
  fi

  if [[ -n "${HOOK_PAYLOAD:-}" ]]; then
    printf '%s' "$HOOK_PAYLOAD"
    return
  fi

  if [[ -n "${HOOK_CONTEXT_PATH:-}" && -f "$HOOK_CONTEXT_PATH" ]]; then
    sed -n '1,80p' "$HOOK_CONTEXT_PATH"
    return
  fi

  if [[ ! -t 0 ]]; then
    sed -n '1,80p'
  fi
}

classify_context() {
  local context="$1"

  case "$context" in
    *install*|*upgrade*|*configure*|*package*|*extension*|*kubectl*|*helm*|*terraform*|*gcloud*|*aws*|*az*|*npm*|*pnpm*|*yarn*|*pip*|*uv*|*cargo*|*go\ get*|*gh\ *)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

payload="$(read_context)"

if [[ -z "$payload" ]]; then
  echo "HOOK_INSTRUCTION: If the next tool call uses a third-party CLI, install step, config schema, SDK, or cloud service, verify current upstream docs first."
  exit 0
fi

if classify_context "$payload"; then
  echo "HOOK_INSTRUCTION: The untrusted host payload appears to involve external tooling or configuration. Verify current upstream docs before running it."
else
  echo "HOOK_INSTRUCTION: No external-doc check was detected from the untrusted host payload. Continue with normal repository-aware caution."
fi
