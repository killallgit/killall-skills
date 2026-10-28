#!/usr/bin/env bash
command -v jq >/dev/null || { echo 'Blocked: jq is required to guard merges' >&2; exit 2; }
cmd=$(jq -r '.tool_input.command') || { echo 'Blocked: cannot read the command to guard' >&2; exit 2; }
merge_re='gh[[:space:]]+(([^[:space:];&|]+[[:space:]]+)*)pr[[:space:]]+merge([^;&|]*)'
[[ "$cmd" =~ $merge_re ]] || exit 0

root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
[[ -f "$root/.coderabbit.yaml" ]] || exit 0

read -ra words <<< "${BASH_REMATCH[1]} ${BASH_REMATCH[3]}"
repo=() pr=() skip=
for word in "${words[@]}"; do
  if [[ -n "$skip" ]]; then
    [[ "$skip" == repo ]] && repo=(-R "$word")
    skip=; continue
  fi
  case "$word" in
    -R|--repo) skip=repo ;;
    --repo=*) repo=(-R "${word#--repo=}") ;;
    -b|--body|-F|--body-file|-t|--subject|-A|--author-email|--match-head-commit) skip=other ;;
    -*) ;;
    *) pr+=("$word") ;;
  esac
done
if (( ${#pr[@]} > 1 )); then
  echo 'Blocked: cannot tell which PR is being merged' >&2; exit 2
fi

checks=$(mktemp)
trap 'rm -f "$checks"' EXIT
gh pr checks "${pr[@]}" "${repo[@]}" --json name,state > "$checks" &
gh_pid=$!
(sleep "${GUARD_GH_TIMEOUT:-20}"; kill "$gh_pid") >/dev/null 2>&1 </dev/null &
watchdog=$!
wait "$gh_pid" 2>/dev/null; gh_status=$?
kill "$watchdog" 2>/dev/null

if (( gh_status != 0 )) || ! jq -e '.[] | select(.name=="CodeRabbit") | select(.state=="SUCCESS")' "$checks" >/dev/null; then
  echo 'Blocked: CodeRabbit review not complete' >&2; exit 2
fi
