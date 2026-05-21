#!/usr/bin/env bash

set -euo pipefail

exit_code="${HOOK_EXIT_CODE:-${1:-0}}"

case "$exit_code" in
  ''|*[!0-9]*)
    exit_code="unknown"
    ;;
esac

if [[ "$exit_code" == "0" ]]; then
  exit 0
fi

echo "HOOK_INSTRUCTION: The previous tool call failed with exit code $exit_code."
echo "HOOK_INSTRUCTION: Capture the failing command, the relevant output, and the smallest reproducible next step."
echo "HOOK_INSTRUCTION: If the failure involves an external tool or config format, re-check current upstream docs before retrying."
