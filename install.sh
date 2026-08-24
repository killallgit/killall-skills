#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MARKETPLACE=killallgit
ACTION=install
DOMAINS=(planning engineering architecture knowledge experimental)
SELECTED=()
INSTALL_ALL=false
LIST_ONLY=false
FAILED=()

usage() {
  cat <<'EOF'
Usage: ./install.sh [--remove] <domain> [domain...]
       ./install.sh [--remove] --all
       ./install.sh --list

Install or remove selected domain plugins in every supported host on PATH.

  --all     Select every domain
  --list    List available domains
  --remove  Remove selected domains instead of installing them
  --help    Show this help
EOF
}

is_domain() {
  local candidate=$1
  local domain
  for domain in "${DOMAINS[@]}"; do
    [ "$candidate" = "$domain" ] && return 0
  done
  return 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --remove) ACTION=remove ;;
    --all) INSTALL_ALL=true ;;
    --list) LIST_ONLY=true ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      echo "unknown argument: $1 (try --help)" >&2
      exit 1
      ;;
    *) SELECTED+=("$1") ;;
  esac
  shift
done

if [ "$LIST_ONLY" = true ]; then
  printf '%s\n' "${DOMAINS[@]}"
  exit 0
fi

if [ "$INSTALL_ALL" = true ]; then
  if [ ${#SELECTED[@]} -gt 0 ]; then
    echo "--all cannot be combined with domain names" >&2
    exit 1
  fi
  SELECTED=("${DOMAINS[@]}")
fi

if [ ${#SELECTED[@]} -eq 0 ]; then
  usage
  exit 1
fi

for domain in "${SELECTED[@]}"; do
  if ! is_domain "$domain"; then
    echo "unknown domain: $domain (try --list)" >&2
    exit 1
  fi
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
    return 0
  }

  if [ "$ACTION" = remove ]; then
    for domain in "${SELECTED[@]}"; do
      say "Claude Code: removing $domain"
      claude plugin uninstall "$domain@$MARKETPLACE" || true
    done
    return 0
  fi

  say "Claude Code: installing ${SELECTED[*]}"
  claude plugin marketplace add "$REPO" 2>/dev/null \
    || claude plugin marketplace update "$MARKETPLACE" \
    || return 1
  for domain in "${SELECTED[@]}"; do
    claude plugin install "$domain@$MARKETPLACE" && continue
    claude plugin uninstall "$domain@$MARKETPLACE" >/dev/null 2>&1 || true
    claude plugin install "$domain@$MARKETPLACE" || return 1
  done
}

install_codex() {
  have codex || {
    echo "codex not found — skipping Codex."
    return 0
  }

  if [ "$ACTION" = remove ]; then
    for domain in "${SELECTED[@]}"; do
      say "Codex: removing $domain"
      codex plugin remove "$domain@$MARKETPLACE" || true
    done
    return 0
  fi

  say "Codex: installing ${SELECTED[*]}"
  codex plugin marketplace add "$REPO" 2>/dev/null \
    || codex plugin marketplace upgrade "$MARKETPLACE" \
    || return 1
  for domain in "${SELECTED[@]}"; do
    codex plugin add "$domain@$MARKETPLACE" && continue
    codex plugin remove "$domain@$MARKETPLACE" >/dev/null 2>&1 || true
    codex plugin add "$domain@$MARKETPLACE" || return 1
  done
}

install_claude || FAILED+=("Claude Code")
install_codex || FAILED+=(Codex)

if [ ${#FAILED[@]} -gt 0 ]; then
  printf '\n%s\n' "Failed ($ACTION) in: ${FAILED[*]}" >&2
  exit 1
fi

say "Done ($ACTION). Restart Claude Code and Codex to apply."
