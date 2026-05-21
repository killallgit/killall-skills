#!/usr/bin/env bash

set -euo pipefail

echo "HOOK_INSTRUCTION: Before ending the session, identify whether the repository has durable memory or project context docs."
echo "HOOK_INSTRUCTION: If the session changed durable knowledge, update the appropriate docs or emit a concise handoff explaining what should be updated."
echo "HOOK_INSTRUCTION: If nothing durable changed, say so in the final response."
