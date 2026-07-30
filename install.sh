#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MARKETPLACE=killallgit
PLUGIN=killall-skills
ACTION=install

while [ $# -gt 0 ]; do
  case "$1" in
    --remove) ACTION=remove ;;
    -h|--help)
      cat <<'EOF'
Usage: ./install.sh [--remove]

Install or refresh killall-skills for every supported host found on PATH.

  --remove  Uninstall the plugin from Claude Code and Codex
  --help    Show this help
EOF
      exit 0
      ;;
    *)
      echo "unknown argument: $1 (try --help)" >&2
      exit 1
      ;;
  esac
  shift
done

say() {
  printf '\n\033[1m==> %s\033[0m\n' "$*"
}

have() {
  command -v "$1" >/dev/null 2>&1
}

install_claude() {
  have claude || {
    echo "claude not found — skipping Claude Code."
    return
  }

  if [ "$ACTION" = remove ]; then
    say "Claude Code: removing plugin"
    claude plugin uninstall "$PLUGIN@$MARKETPLACE" || true
    return
  fi

  say "Claude Code: installing plugin"
  claude plugin marketplace add "$REPO" 2>/dev/null \
    || claude plugin marketplace update "$MARKETPLACE"
  claude plugin uninstall "$PLUGIN@$MARKETPLACE" >/dev/null 2>&1 || true
  claude plugin install "$PLUGIN@$MARKETPLACE"
}

install_codex() {
  have codex || {
    echo "codex not found — skipping Codex."
    return
  }

  if [ "$ACTION" = remove ]; then
    say "Codex: removing plugin"
    codex plugin remove "$PLUGIN@$MARKETPLACE" || true
    return
  fi

  say "Codex: installing plugin"
  codex plugin marketplace add "$REPO" 2>/dev/null || true
  codex plugin remove "$PLUGIN@$MARKETPLACE" >/dev/null 2>&1 || true
  codex plugin add "$PLUGIN@$MARKETPLACE"
}

install_claude
install_codex

say "Done ($ACTION). Restart Claude Code and Codex to apply."
