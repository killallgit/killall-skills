#!/usr/bin/env bash
# Block until a GitHub Actions run reaches a terminal state, then report.
#
# One blocking call. While the run is healthy this prints a line per state
# change and nothing else; logs never reach the caller unless the run fails.
# They are pulled to disk as each job finishes, and only the failing tail is
# echoed.
#
# Usage:
#   wait-for-action.sh --run-id <id> [options]
#   wait-for-action.sh                      # newest run for the current HEAD
#
# Options:
#   --run-id ID        workflow run to watch
#   --repo OWNER/REPO  repository (default: the one in cwd)
#   --ttl DURATION     total budget: 45s, 15m, 1h (default 15m)
#   --tail N           log lines to echo on failure (default 40)
#   --log-dir PATH     where to keep logs (default /tmp/actions/<run-id>)
#   --no-fail-fast     wait for the whole run instead of bailing on the first
#                      failed job
#   --quiet            print only the terminal line and any failure log
#   -h, --help         this text
#
# Poll schedule - dense while failures are likely, sparse once the run has
# settled into real work:
#   0-90s      every 15s
#   90s-3.5m   every 30s
#   3.5m-5.5m  every 60s
#   5.5m+      every 3m
#
# Exit: 0 success  1 failed  2 ttl expired  3 usage or API error

set -euo pipefail

RUN_ID=""
REPO=""
TTL=900
TAIL=40
LOG_DIR=""
FAIL_FAST=1
QUIET=0

die() { printf 'wait-for-action.sh: %s\n' "$*" >&2; exit 3; }
usage() { sed -n '2,/^set -/p' "$0" | sed 's/^# \{0,1\}//; /^set -/d'; }

# 90 -> 90, 15m -> 900, 1h -> 3600
parse_duration() {
  local v="$1" n="${1%[smh]}"
  [[ "$n" =~ ^[0-9]+$ && "$n" -gt 0 ]] || die "bad duration: $v"
  case "$v" in
    *h) echo $(( n * 3600 )) ;;
    *m) echo $(( n * 60 )) ;;
    *)  echo "$n" ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-id)    RUN_ID="${2:?--run-id needs a value}"; shift 2 ;;
    --run-id=*)  RUN_ID="${1#*=}"; shift ;;
    --repo)      REPO="${2:?--repo needs a value}"; shift 2 ;;
    --repo=*)    REPO="${1#*=}"; shift ;;
    --ttl)       TTL=$(parse_duration "${2:?--ttl needs a value}"); shift 2 ;;
    --ttl=*)     TTL=$(parse_duration "${1#*=}"); shift ;;
    --tail)      TAIL="${2:?--tail needs a value}"; shift 2 ;;
    --tail=*)    TAIL="${1#*=}"; shift ;;
    --log-dir)   LOG_DIR="${2:?--log-dir needs a value}"; shift 2 ;;
    --log-dir=*) LOG_DIR="${1#*=}"; shift ;;
    --no-fail-fast) FAIL_FAST=0; shift ;;
    --quiet)     QUIET=1; shift ;;
    -h|--help)   usage; exit 0 ;;
    *)           die "unknown argument: $1" ;;
  esac
done

[[ "$TAIL" =~ ^[0-9]+$ ]] || die "--tail must be an integer"
command -v gh >/dev/null || die "gh CLI not found"
command -v jq >/dev/null || die "jq not found"

REPO_ARG=()
[[ -n "$REPO" ]] && REPO_ARG=(--repo "$REPO")

START=$(date +%s)
elapsed() { echo $(( $(date +%s) - START )); }

POLL_LOG=""
# Everything the script emits is also kept in poll.log, so a --quiet run still
# leaves a full trace on disk.
emit() {
  local line
  printf -v line '[t=%ss] %s' "$(elapsed)" "$2"
  [[ -n "$POLL_LOG" ]] && printf '%s\n' "$line" >>"$POLL_LOG"
  if [[ "$1" == always ]] || (( ! QUIET )); then
    printf '%s\n' "$line"
  fi
  return 0
}

if [[ -z "$RUN_ID" ]]; then
  [[ -n "$REPO" ]] && die "--repo requires --run-id"
  sha=$(git rev-parse HEAD 2>/dev/null) || die "not a git repository - pass --run-id"
  RUN_ID=$(gh run list --commit "$sha" --limit 1 --json databaseId \
    --jq '.[0].databaseId // empty' 2>/dev/null || true)
  [[ -n "$RUN_ID" ]] || die "no workflow run found for $sha - pass --run-id"
fi
[[ "$RUN_ID" =~ ^[0-9]+$ ]] || die "--run-id must be numeric, got: $RUN_ID"

: "${LOG_DIR:=/tmp/actions/$RUN_ID}"
mkdir -p "$LOG_DIR/jobs"
POLL_LOG="$LOG_DIR/poll.log"
RUN_JSON="$LOG_DIR/run.json"
FAILED_LOG="$LOG_DIR/failed.log"

interval_for() {
  local e=$1
  if   (( e < 90 ));  then echo 15
  elif (( e < 210 )); then echo 30
  elif (( e < 330 )); then echo 60
  else                     echo 180
  fi
}

# One API call per poll. Everything downstream reads run.json, so the jobs and
# their steps cost nothing extra.
fetch() {
  local err
  # Order matters: stderr is dup'd to the capture pipe first, then stdout is
  # pointed at the file. Reversed, gh's error message lands in the file instead.
  if ! err=$(gh run view "$RUN_ID" "${REPO_ARG[@]}" \
      --json status,conclusion,jobs,url,workflowName,displayTitle,headBranch \
      2>&1 >"$RUN_JSON.tmp"); then
    rm -f "$RUN_JSON.tmp"
    FETCH_ERR="$err"
    return 1
  fi
  mv "$RUN_JSON.tmp" "$RUN_JSON"
  return 0
}

BAD='["failure","cancelled","timed_out","startup_failure"]'
FIRST_BAD="[.jobs[] | select(.conclusion as \$c | $BAD | index(\$c))] | first // {}"

field() { jq -r "$1" "$RUN_JSON"; }

# Pull a job's log the moment it completes. Mid-run this is the only way to have
# the failing job's output already on disk when we bail out.
declare -A SAVED=()
save_completed_logs() {
  local id name slug
  while IFS=$'\037' read -r id name; do
    [[ -z "$id" || -n "${SAVED[$id]:-}" ]] && continue
    SAVED[$id]=1
    slug="${name//[^a-zA-Z0-9._-]/_}"
    gh run view "${REPO_ARG[@]}" --job "$id" --log >"$LOG_DIR/jobs/$slug.log" 2>/dev/null \
      || rm -f "$LOG_DIR/jobs/$slug.log"
  done < <(jq -r '.jobs[] | select(.status=="completed")
                  | "\(.databaseId)\u001f\(.name)"' "$RUN_JSON")
  return 0
}

# gh prefixes every log line with "job<TAB>step<TAB>timestamp", and opens each
# step with a BOM. Drop the job column (the caller already knows it) and the
# timestamps (they only eat width), and keep the step as a short [prefix].
fmt_log() {
  awk -F'\t' -v bom="$(printf '\357\273\277')" '
    {
      if (NF >= 3) { step = $2; msg = $0; sub(/^[^\t]*\t[^\t]*\t/, "", msg) }
      else         { step = "";  msg = $0 }
      sub("^" bom, "", msg)
      sub(/^[0-9][0-9-]*T[0-9:.]+Z /, "", msg)
      if (step != "") printf "[%s] %s\n", step, msg; else print msg
    }' "$1"
}

# Console gets the error markers and a bounded tail; the full log stays on disk.
report_failure_log() {
  local job="$1" job_id="$2" errs
  # A previous invocation against this run id left its own failed.log here.
  # Clear it so a fetch that comes back empty cannot pass off stale output.
  rm -f "$FAILED_LOG"
  if [[ -n "$job_id" ]]; then
    gh run view "${REPO_ARG[@]}" --job "$job_id" --log >"$FAILED_LOG" 2>/dev/null || true
  fi
  if [[ ! -s "$FAILED_LOG" ]]; then
    gh run view "$RUN_ID" "${REPO_ARG[@]}" --log-failed >"$FAILED_LOG" 2>/dev/null || true
  fi
  if [[ ! -s "$FAILED_LOG" ]]; then
    printf -- '--- no log available for %s ---\n' "${job:-the failed job}"
    return 0
  fi

  errs=$(fmt_log "$FAILED_LOG" | grep -aF '##[error]' | head -20 || true)
  if [[ -n "$errs" ]]; then
    printf -- '--- error lines ---\n%s\n' "$errs"
  fi
  printf -- '--- last %s lines of %s ---\n' "$TAIL" "${job:-failed steps}"
  fmt_log "$FAILED_LOG" | tail -n "$TAIL"
  printf -- '--- full logs: %s ---\n' "$LOG_DIR"
  return 0
}

finish_failed() {
  local conclusion="$1" job job_id step
  job=$(field "$FIRST_BAD | .name // \"\"")
  job_id=$(field "$FIRST_BAD | .databaseId // \"\"")
  step=$(field "$FIRST_BAD | .steps // [] | [.[] | select(.conclusion as \$c | $BAD | index(\$c))] | first // {} | .name // \"\"")
  emit always "FAILED $conclusion${job:+ job='$job'}${step:+ step='$step'} $(field '.url')"
  report_failure_log "$job" "$job_id"
  exit 1
}

errors=0
last=""

while :; do
  if ! fetch; then
    errors=$(( errors + 1 ))
    # A run created seconds ago can 404 until GitHub catches up, so early
    # failures are retried. A persistent one means the id or repo is wrong.
    if (( errors >= 3 )) || (( $(elapsed) > 60 )); then
      emit always "ERROR $FETCH_ERR"
      exit 3
    fi
    emit normal "PENDING api-error, retrying -- $FETCH_ERR"
  else
    errors=0
    save_completed_logs

    status=$(field '.status')
    conclusion=$(field '.conclusion // ""')
    failed_jobs=$(field "[.jobs[] | select(.conclusion as \$c | $BAD | index(\$c))] | length")

    if [[ "$status" == "completed" ]]; then
      case "$conclusion" in
        success|skipped|neutral)
          emit always "DONE $conclusion $(field '.url')"
          emit normal "logs: $LOG_DIR"
          exit 0 ;;
        *) finish_failed "$conclusion" ;;
      esac
    fi

    # The run keeps going after a job fails, but the answer is already known and
    # the failing job's log is already on disk. Stop paying for the rest.
    if (( FAIL_FAST )) && (( failed_jobs > 0 )); then
      finish_failed "job-failed"
    fi

    state=$(field '
      [ .status,
        ("jobs=" + ([.jobs[] | select(.status=="completed")] | length | tostring)
                 + "/" + (.jobs | length | tostring)),
        ([.jobs[] | select(.status!="completed") | .name] | first // ""
          | if . == "" then "" else "at=" + . end)
      ] | map(select(. != "" and . != null)) | join(" ")')
    [[ "$state" != "$last" ]] && emit normal "PENDING $state"
    last="$state"
  fi

  remaining=$(( TTL - $(elapsed) ))
  if (( remaining <= 0 )); then
    emit always "TIMEOUT still $(field '.status') after ${TTL}s -- $(field '.url')"
    emit normal "logs so far: $LOG_DIR"
    exit 2
  fi
  nap=$(interval_for "$(elapsed)")
  (( nap > remaining )) && nap=$remaining
  sleep "$nap"
done
