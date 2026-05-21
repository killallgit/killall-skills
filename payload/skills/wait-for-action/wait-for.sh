#!/usr/bin/env bash
# Poll an async action with adaptive backoff. Single blocking call — zero
# conversation tokens during the wait.
#
# Usage:
#   wait-for.sh <kind> <args...> [--profile quick|long]
#
# Kinds:
#   coderabbit [pr]        wait for CodeRabbit review on PR (auto-detect if no pr)
#   gh-checks  [pr]        wait for all PR status checks
#   gh-action  <run-id> [repo]
#                          wait for a GitHub Actions run
#
# Profiles:
#   quick (default) — actions expected within ~1 min
#   long            — multi-minute actions (CodeRabbit, full builds)
#
# Behavior:
#   - First probe always at t=30s (catches immediate failures)
#   - Adaptive backoff after that
#   - Hard cap: 10 min total
#   - One stdout line per probe: "[t=Xs] STATE detail"
#   - Exit 0 done-ok, 1 done-fail, 2 timeout, 3 usage error

set -euo pipefail

CAP=600
PROFILE="quick"
KIND=""
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --profile=*) PROFILE="${1#*=}"; shift ;;
    -h|--help) sed -n '2,/^set -/p' "$0" | sed 's/^# \{0,1\}//;/^set -/d'; exit 0 ;;
    *) if [[ -z "$KIND" ]]; then KIND="$1"; else ARGS+=("$1"); fi; shift ;;
  esac
done

case "$KIND" in
  coderabbit|gh-checks|gh-action) ;;
  *) echo "usage: wait-for.sh <coderabbit|gh-checks|gh-action> [args] [--profile quick|long]" >&2; exit 3 ;;
esac

case "$PROFILE" in
  quick) intervals=(30 30 60 60 90 120 120 120) ;;
  long)  intervals=(60 90 120 150 180 240) ;;
  *) echo "bad profile: $PROFILE" >&2; exit 3 ;;
esac

resolve_pr() {
  local pr="${1:-}"
  if [[ -z "$pr" ]]; then
    pr=$(gh pr view --json number --jq .number 2>/dev/null || true)
  fi
  echo "$pr"
}

probe_coderabbit() {
  local pr; pr=$(resolve_pr "${ARGS[0]:-}")
  [[ -z "$pr" ]] && { echo "no-pr"; return 1; }

  local state
  state=$(gh pr checks "$pr" --json name,state 2>/dev/null \
    | jq -r '.[] | select(.name|test("coderabbit";"i")) | .state' | head -1)

  case "${state:-PENDING}" in
    SUCCESS)              echo "review-done";        return 0 ;;
    FAILURE|CANCEL*|SKIP*) echo "review-$state";     return 1 ;;
    PENDING|"")           echo "pr=$pr";             return 2 ;;
    *)                    echo "unknown=$state";     return 2 ;;
  esac
}

probe_gh_checks() {
  local pr; pr=$(resolve_pr "${ARGS[0]:-}")
  [[ -z "$pr" ]] && { echo "no-pr"; return 1; }

  local out
  out=$(gh pr checks "$pr" --json state --jq \
    '{p:(map(select(.state=="PENDING"))|length),f:(map(select(.state=="FAILURE" or .state=="CANCELLED"))|length),t:length}')
  local p f t
  p=$(jq -r .p <<<"$out"); f=$(jq -r .f <<<"$out"); t=$(jq -r .t <<<"$out")

  if (( f > 0 )); then echo "failed=$f/$t"; return 1; fi
  if (( p > 0 )); then echo "pending=$p/$t"; return 2; fi
  echo "all-passed=$t"; return 0
}

probe_gh_action() {
  local id="${ARGS[0]:?run-id required}"
  local repo="${ARGS[1]:-}"
  local repo_arg=()
  [[ -n "$repo" ]] && repo_arg=(--repo "$repo")

  local out
  out=$(gh run view "$id" "${repo_arg[@]}" --json status,conclusion --jq '"\(.status):\(.conclusion // "null")"' 2>/dev/null)
  case "$out" in
    completed:success)        echo "$out"; return 0 ;;
    completed:*)              echo "$out"; return 1 ;;
    *)                        echo "$out"; return 2 ;;
  esac
}

probe() {
  case "$KIND" in
    coderabbit) probe_coderabbit ;;
    gh-checks)  probe_gh_checks ;;
    gh-action)  probe_gh_action ;;
  esac
}

start=$(date +%s)
elapsed() { echo $(( $(date +%s) - start )); }
log() { echo "[t=$(elapsed)s] $1 $2"; }

sleep 30

idx=0
while :; do
  e=$(elapsed)
  if (( e >= CAP )); then echo "[t=${e}s] TIMEOUT"; exit 2; fi

  set +e; detail=$(probe); rc=$?; set -e
  case $rc in
    0) log "DONE" "$detail"; exit 0 ;;
    1) log "FAILED" "$detail"; exit 1 ;;
    2) log "PENDING" "$detail" ;;
  esac

  if (( idx < ${#intervals[@]} )); then
    wait_s=${intervals[$idx]}
  else
    wait_s=${intervals[-1]}
  fi
  idx=$((idx+1))

  remaining=$(( CAP - e ))
  if (( wait_s > remaining )); then wait_s=$remaining; fi
  if (( wait_s <= 0 )); then echo "[t=${e}s] TIMEOUT"; exit 2; fi

  sleep "$wait_s"
done
