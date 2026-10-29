#!/usr/bin/env bash
merge_re='(^|[^[:alnum:]_.-])gh[[:space:]]+(([^[:space:];&|]+[[:space:]]+)*)pr[[:space:]]+merge([^;&|]*)'
cd_re='cd[[:space:]]+([^[:space:];&|]+)'
input=$(cat)
if ! command -v jq >/dev/null; then
  # No jq to parse the hook input: leave unrelated commands alone, block merges.
  [[ "$input" =~ $merge_re ]] || exit 0
  echo 'Blocked: jq is required to guard merges' >&2; exit 2
fi
cmd=$(jq -r '.tool_input.command' <<< "$input") || { echo 'Blocked: cannot read the command to guard' >&2; exit 2; }
[[ "$cmd" =~ $merge_re ]] || exit 0
match=${BASH_REMATCH[0]} before=${BASH_REMATCH[2]} after=${BASH_REMATCH[4]}
rest=${cmd#*"$match"}
if [[ "$rest" =~ $merge_re ]]; then
  echo 'Blocked: more than one merge in one command; merge them separately' >&2; exit 2
fi

# The merge runs wherever the command last cd'd to, so guard that repo.
prefix=${cmd%%"$match"*}
while [[ "$prefix" =~ $cd_re ]]; do
  dir=${BASH_REMATCH[1]}
  prefix=${prefix#*"${BASH_REMATCH[0]}"}
done
dir=${dir/#\~/$HOME}
[[ -n "${dir:-}" && -d "$dir" ]] && cd "$dir"

read -ra words <<< "$before $after"
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

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# Run a command with its output in $work/out and $work/err, killed after the
# timeout so a stalled gh cannot let the hook time out into an allowed merge.
bounded() {
  "$@" >"$work/out" 2>"$work/err" &
  local pid=$! watchdog status
  (sleep "${GUARD_GH_TIMEOUT:-20}"; kill "$pid") >/dev/null 2>&1 </dev/null &
  watchdog=$!
  wait "$pid" 2>/dev/null; status=$?
  kill "$watchdog" 2>/dev/null
  return "$status"
}

# Enforce only where CodeRabbit is configured: in the target repo for -R,
# otherwise in the repo the merge runs in. Only a definite "no config" leaves
# the merge unguarded; any other lookup failure blocks.
if (( ${#repo[@]} )); then
  if ! bounded gh api "repos/${repo[1]}/contents/.coderabbit.yaml"; then
    grep -q 'HTTP 404' "$work/err" && exit 0
    echo "Blocked: could not tell whether ${repo[1]} uses CodeRabbit" >&2; exit 2
  fi
else
  root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  [[ -f "$root/.coderabbit.yaml" ]] || exit 0
fi

bounded gh pr checks "${pr[@]}" "${repo[@]}" --json name,state,description
gh_status=$?

# gh pr checks exits 1 when any check failed and 8 when any is pending; the
# JSON is still complete, and only the CodeRabbit check matters here.
case "$gh_status" in 0|1|8) ;; *) echo 'Blocked: could not read the PR checks' >&2; exit 2 ;; esac

if ! jq -e '.[] | select(.name=="CodeRabbit" and .state=="SUCCESS" and ((.description // "") | test("rate limit|skip|paus"; "i") | not))' "$work/out" >/dev/null; then
  echo 'Blocked: CodeRabbit review not complete' >&2; exit 2
fi
