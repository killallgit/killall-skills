#!/usr/bin/env bash

set -euo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HOOK_DIR/../.." && pwd)"

echo "HOOK_INSTRUCTION: Treat $REPO_ROOT as a tool-agnostic skill pack."
echo "HOOK_INSTRUCTION: Read AGENTS.md first, then inspect skills/, rules/, and hooks/ as needed."
echo "HOOK_INSTRUCTION: Before installing into a host tool, check that tool's current documentation and preserve user config."
echo "HOOK_INSTRUCTION: Prefer symlinks for local development and copies for portable installs."
