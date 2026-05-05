#!/usr/bin/env bash
# Run claude --bare with only this plugin's skills loaded.
# Usage:
#   scripts/skill.sh "<prompt>" [extra claude flags...]
#   echo "<prompt>" | scripts/skill.sh
#
# Requires: ANTHROPIC_API_KEY in env.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "ANTHROPIC_API_KEY not set" >&2
  exit 1
fi

ALLOWED_TOOLS="${ALLOWED_TOOLS:-Skill,Read,Edit,Write,Bash,Glob,Grep}"

if [[ $# -gt 0 ]]; then
  PROMPT="$1"; shift
  exec claude --bare -p "$PROMPT" \
    --plugin-dir "$REPO_ROOT" \
    --allowedTools "$ALLOWED_TOOLS" \
    "$@"
else
  exec claude --bare -p \
    --plugin-dir "$REPO_ROOT" \
    --allowedTools "$ALLOWED_TOOLS" \
    "$@"
fi
