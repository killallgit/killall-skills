#!/usr/bin/env bash
# Block until a GitHub Actions run reaches a terminal state, then report.
#
# One blocking call. While the run is healthy this prints a line per state
# change and nothing else; logs never reach the caller unless the run fails.
# They are pulled to disk as each job finishes, and only the failing tail is
# echoed.
#
# Usage:
#   wait-for-action.sh --checks [--pr N]   # every check on the PR, any source
#   wait-for-action.sh --ready [--pr N]     # --checks, then the review the repo runs
#   wait-for-action.sh --run-id <id> [options]
#   wait-for-action.sh                      # newest run for the current HEAD
#   wait-for-action.sh --coderabbit         # CodeRabbit review of HEAD instead
#   wait-for-action.sh --pr-agent           # PR-Agent review of HEAD instead
#
# Options:
#   --checks           wait until every check on the PR head has finished.
#                      That is Actions runs, other check runs, and commit
#                      statuses — anything `gh pr checks` reports. Use this
#                      to confirm CI. With no flags the script still watches
#                      only the newest Actions run for HEAD.
#   --ready            ready to merge: --checks, then, when a "CodeRabbit" check
#                      or a pr-agent check exists, that review of the PR head.
#                      One terminal line and one exit code for both, one --ttl
#                      for both. CodeRabbit wins when both run. Without a
#                      reviewer it is --checks. Review files land in
#                      <log-dir>/review
#   --pr N             pull request number for --checks, --ready, --coderabbit
#                      and --pr-agent (default with --checks and --ready: the
#                      open PR for the current branch). The review waits read
#                      the PR's head commit from it
#   --sha COMMIT       commit to watch, for a checkout where `git rev-parse
#                      HEAD` fails. Applies to --coderabbit, --pr-agent,
#                      --ready and the no-flag run lookup, not to --checks
#   --run-id ID        workflow run to watch
#   --repo OWNER/REPO  repository (default: the one in cwd)
#   --ttl DURATION     total budget: 45s, 15m, 1h (default 15m)
#   --tail N           log lines to echo on failure (default 40)
#   --log-dir PATH     where to keep logs (default /tmp/actions/<run-id>,
#                      or /tmp/actions/pr-<n> with --checks)
#   --no-fail-fast     wait for the whole run, or for every check to finish,
#                      instead of bailing on the first failure
#   --quiet            print only the terminal line and any failure log
#   --coderabbit       wait for the CodeRabbit review of HEAD, not an Actions
#                      run. CodeRabbit is a GitHub App, so it is polled through
#                      its "CodeRabbit" check run (see coderabbit.py). A rate
#                      limited or skipped review is restarted by commenting
#                      "@coderabbitai review"
#   --pr-agent         wait for the PR-Agent review of HEAD, not an Actions
#                      run. PR-Agent answers with one comment, not a check run
#                      (see pr_agent.py). A missing review is started by
#                      commenting "/review"
#   --no-trigger       with --coderabbit, --pr-agent or --ready: report instead
#                      of commenting
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
#       4 CodeRabbit did not review (--coderabbit and --ready)
#       5 no check ever appeared (--checks and --ready)
#       (--pr-agent uses 0, 2 and 3 only)
#
# --checks classification, from the check's own state. `gh pr checks` leaves
# STARTUP_FAILURE and STALE in its pending bucket and treats CANCELLED as
# neither a pass nor a fail, so the bucket is only a fallback:
#   pass     SUCCESS
#   skipping SKIPPED, NEUTRAL (both count as passed)
#   fail     FAILURE, ERROR, TIMED_OUT, ACTION_REQUIRED, STARTUP_FAILURE,
#            STALE, CANCELLED
#   pending  QUEUED, IN_PROGRESS, WAITING, PENDING, REQUESTED, EXPECTED
# An empty rollup is retried for 2 minutes (or until --ttl, when that is
# shorter), then exit 5. A green result waits until the set of check names
# has stayed unchanged for 10 seconds, so a check that registers late is
# included. A failure returns immediately unless --no-fail-fast.

set -euo pipefail

RUN_ID=""
REPO=""
TTL=900
TAIL=40
LOG_DIR=""
FAIL_FAST=1
QUIET=0
CODERABBIT=0
PR_AGENT=0
NO_TRIGGER=0
CHECKS=0
READY=0
PR=""
SHA=""

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
    --coderabbit) CODERABBIT=1; shift ;;
    --pr-agent)  PR_AGENT=1; shift ;;
    --checks)    CHECKS=1; shift ;;
    --ready)     READY=1; shift ;;
    --pr)        PR="${2:?--pr needs a value}"; shift 2 ;;
    --pr=*)      PR="${1#*=}"; shift ;;
    --sha)       SHA="${2:?--sha needs a value}"; shift 2 ;;
    --sha=*)     SHA="${1#*=}"; shift ;;
    --no-trigger) NO_TRIGGER=1; shift ;;
    -h|--help)   usage; exit 0 ;;
    *)           die "unknown argument: $1" ;;
  esac
done

[[ "$TAIL" =~ ^[0-9]+$ ]] || die "--tail must be an integer"
(( ! NO_TRIGGER || CODERABBIT || PR_AGENT || READY )) || die "--no-trigger only applies to --coderabbit, --pr-agent or --ready"
(( ! CODERABBIT || ! PR_AGENT )) || die "--coderabbit and --pr-agent are separate waits; run one, then the other"
# `&&` binds tighter than `||`: checks mode excludes the review waits.
(( CHECKS == 0 || PR_AGENT == 0 && CODERABBIT == 0 )) || die "--checks does not combine with --coderabbit or --pr-agent"
(( READY == 0 || CHECKS == 0 && PR_AGENT == 0 && CODERABBIT == 0 )) || die "--ready already covers --checks, --coderabbit and --pr-agent; use it alone"
[[ -z "$RUN_ID" || "$CHECKS" -eq 0 && "$READY" -eq 0 ]] || die "--checks and --ready do not combine with --run-id"
(( CHECKS || READY || CODERABBIT || PR_AGENT )) || [[ -z "$PR" ]] || die "--pr only applies to --checks, --ready, --coderabbit or --pr-agent"
[[ -z "$SHA" || "$CHECKS" -eq 0 ]] || die "--sha does not apply to --checks: the PR rollup already follows the PR head"
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

interval_for() {
  local e=$1
  if   (( e < 90 ));  then echo 15
  elif (( e < 210 )); then echo 30
  elif (( e < 330 )); then echo 60
  else                     echo 180
  fi
}

# Replaces the shell, so the review wait is always the last thing a run does.
# Needs the commit under review: --sha, else the head of --pr, else git's HEAD.
run_review() {
  local script=$1 ttl=$2 log_dir=$3 here args
  if [[ -z "$SHA" && -n "$PR" ]]; then
    [[ "$PR" =~ ^[0-9]+$ ]] || die "--pr must be numeric, got: $PR"
    SHA=$(gh pr view "$PR" "${REPO_ARG[@]}" --json headRefOid --jq .headRefOid 2>/dev/null) \
      || die "cannot read the head commit of PR $PR"
  fi
  here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
  args=(--ttl "$ttl" --elapsed "$(elapsed)")
  (( QUIET )) && args+=(--quiet)
  (( NO_TRIGGER )) && args+=(--no-trigger)
  [[ -n "$log_dir" ]] && args+=(--log-dir "$log_dir")
  [[ -n "$SHA" ]] && args+=(--sha "$SHA")
  if command -v uv >/dev/null; then
    exec uv run --no-project "$here/$script" "${args[@]}"
  fi
  exec python3 "$here/$script" "${args[@]}"
}

if (( CODERABBIT || PR_AGENT )); then
  [[ -z "$RUN_ID$REPO" ]] || die "--coderabbit and --pr-agent watch HEAD; drop --run-id and --repo"
  script=coderabbit.py
  (( PR_AGENT )) && script=pr_agent.py
  run_review "$script" "$TTL" "$LOG_DIR"
fi

if (( ! CHECKS && ! READY )); then
  if [[ -z "$RUN_ID" ]]; then
    [[ -n "$REPO" ]] && die "--repo requires --run-id"
    sha=${SHA:-$(git rev-parse HEAD 2>/dev/null)} || die "not a git repository - pass --run-id or --sha"
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
fi

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
  if [[ ! -s "$FAILED_LOG" && -n "$RUN_ID" ]]; then
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

# `gh pr checks --json` exits 0 whenever the rollup is non-empty, including
# when checks have failed, and exits 1 with "no checks reported" when the
# rollup is empty. The JSON on stdout is the source of truth either way.
fetch_checks() {
  local err
  if err=$(gh pr checks "$PR" "${REPO_ARG[@]}" \
      --json name,state,bucket,link,workflow,completedAt \
      2>&1 >"$CHECKS_JSON.tmp"); then
    mv "$CHECKS_JSON.tmp" "$CHECKS_JSON"
    return 0
  fi
  if [[ -s "$CHECKS_JSON.tmp" ]] && jq -e 'type == "array"' "$CHECKS_JSON.tmp" >/dev/null 2>&1; then
    mv "$CHECKS_JSON.tmp" "$CHECKS_JSON"
    return 0
  fi
  # gh prints this on stderr. A build that puts it on stdout lands in the file.
  if [[ "$err" == *"no checks reported"* ]] || grep -q "no checks reported" "$CHECKS_JSON.tmp" 2>/dev/null; then
    echo '[]' >"$CHECKS_JSON"
    rm -f "$CHECKS_JSON.tmp"
    return 0
  fi
  rm -f "$CHECKS_JSON.tmp"
  FETCH_ERR="$err"
  return 1
}

# Bucket is a fallback. gh leaves STARTUP_FAILURE and STALE pending, and
# CANCELLED in its own bucket, and a merge must not treat either as a pass.
CHECKS_JQ='
def klass:
  if .state == "SUCCESS" then "pass"
  elif (.state == "SKIPPED" or .state == "NEUTRAL") then "skip"
  elif (.state == "FAILURE" or .state == "ERROR" or .state == "TIMED_OUT"
        or .state == "ACTION_REQUIRED" or .state == "STARTUP_FAILURE"
        or .state == "STALE" or .state == "CANCELLED") then "fail"
  elif .bucket == "pass" then "pass"
  elif .bucket == "skipping" then "skip"
  elif (.bucket == "fail" or .bucket == "cancel") then "fail"
  elif ((.completedAt // "") | test("^[1-9]")) then "fail"
  else "pending"
  end;
[.[] | . + {klass: klass}] as $rows
| {
    key: ([$rows[].name] | sort | join("\n")),
    pending: ([$rows[] | select(.klass == "pending")] | length),
    pass: ([$rows[] | select(.klass == "pass")] | length),
    skip: ([$rows[] | select(.klass == "skip")] | length),
    fail: ([$rows[] | select(.klass == "fail")] | length),
    at: ([$rows[] | select(.klass == "pending") | .name][0] // ""),
    failed: [$rows[] | select(.klass == "fail") | {name, state, link, workflow: (.workflow // "")}]
  }
'

finish_checks_failed() {
  local name state link workflow logged=0
  while IFS=$'\037' read -r name state link workflow; do
    [[ -z "$name" ]] && continue
    emit always "FAILED state='$state' name='$name'${workflow:+ workflow='$workflow'}${link:+ $link}"
    if (( ! logged )) && [[ "$link" =~ /actions/runs/([0-9]+)/job/([0-9]+) ]]; then
      logged=1
      RUN_ID="${BASH_REMATCH[1]}"
      report_failure_log "$name" "${BASH_REMATCH[2]}"
    fi
  done < <(jq -r '.failed[] | "\(.name)\u001f\(.state)\u001f\(.link)\u001f\(.workflow)"' "$LOG_DIR/summary.json")
  (( logged )) || printf -- '--- checks: %s ---\n' "$LOG_DIR"
  exit 1
}

# The review the repo runs, read from the check rollup: CodeRabbit posts a
# "CodeRabbit" check, PR-Agent runs as a workflow with pr-agent in its name.
# CodeRabbit wins when both run. Empty when the repo has neither.
review_script() {
  jq -r 'if any(.[]; .name == "CodeRabbit") then "coderabbit.py"
         elif any(.[]; ((.name + " " + (.workflow // "")) | test("pr[-_ ]?agent"; "i"))) then "pr_agent.py"
         else "" end' "$CHECKS_JSON"
}

# WFA_REGISTER_FOR, WFA_SETTLE_FOR, and WFA_INTERVAL override the 2 minute
# registration window, the 10 second settle, and the poll interval. Tests set
# them; a normal run leaves them unset.
wait_for_checks() {
  local register_for=${WFA_REGISTER_FOR:-120}
  local settle_for=${WFA_SETTLE_FOR:-10}
  [[ "$register_for" =~ ^[0-9]+$ ]] || die "WFA_REGISTER_FOR must be an integer"
  [[ "$settle_for" =~ ^[0-9]+$ ]] || die "WFA_SETTLE_FOR must be an integer"
  [[ -z "${WFA_INTERVAL:-}" || "${WFA_INTERVAL}" =~ ^[0-9]+$ ]] || die "WFA_INTERVAL must be an integer"

  if [[ -z "$PR" ]]; then
    PR=$(gh pr view "${REPO_ARG[@]}" --json number --jq .number 2>/dev/null) \
      || die "no open PR for the current branch - pass --pr"
  fi
  [[ "$PR" =~ ^[0-9]+$ ]] || die "--pr must be numeric, got: $PR"

  : "${LOG_DIR:=/tmp/actions/pr-$PR}"
  mkdir -p "$LOG_DIR"
  POLL_LOG="$LOG_DIR/poll.log"
  CHECKS_JSON="$LOG_DIR/checks.json"
  FAILED_LOG="$LOG_DIR/failed.log"
  PR_URL=$(gh pr view "$PR" "${REPO_ARG[@]}" --json url --jq .url 2>/dev/null || true)

  local errors=0 seen=0 stable_key="" stable_at=0 last="" nap remaining
  local count key pending=0 pass skip fail at now state
  while :; do
    pending=0
    if ! fetch_checks; then
      errors=$(( errors + 1 ))
      if (( errors >= 3 )) || (( $(elapsed) > 60 )); then
        emit always "ERROR $FETCH_ERR"
        exit 3
      fi
      emit normal "PENDING api-error, retrying -- $FETCH_ERR"
    elif ! jq -c "$CHECKS_JQ" "$CHECKS_JSON" >"$LOG_DIR/summary.json"; then
      emit always "ERROR could not read checks"
      exit 3
    else
      errors=0
      count=$(jq 'length' "$CHECKS_JSON")
      if (( count == 0 )); then
        if (( $(elapsed) >= register_for )); then
          emit always "NONE no checks reported${PR_URL:+ $PR_URL}"
          exit 5
        fi
        state="no checks yet"
        [[ "$state" != "$last" ]] && emit normal "PENDING $state"
        last="$state"
      else
        seen=1
        key=$(jq -r '.key' "$LOG_DIR/summary.json")
        pending=$(jq -r '.pending' "$LOG_DIR/summary.json")
        pass=$(jq -r '.pass' "$LOG_DIR/summary.json")
        skip=$(jq -r '.skip' "$LOG_DIR/summary.json")
        fail=$(jq -r '.fail' "$LOG_DIR/summary.json")
        at=$(jq -r '.at' "$LOG_DIR/summary.json")
        if [[ "$key" != "$stable_key" ]]; then
          stable_key=$key
          stable_at=$(date +%s)
        fi
        if (( fail > 0 )) && { (( FAIL_FAST )) || (( pending == 0 )); }; then
          finish_checks_failed
        fi
        if (( pending == 0 && fail == 0 )); then
          now=$(date +%s)
          if (( now - stable_at >= settle_for )); then
            if (( READY )) && [[ -n "$(review_script)" ]]; then
              emit normal "CI passed ($pass passed, $skip skipped), waiting for the review"
              return 0
            fi
            if (( pass == 0 && skip > 0 )); then
              emit always "DONE skipped${PR_URL:+ $PR_URL}"
            else
              emit always "DONE pass${PR_URL:+ $PR_URL}"
            fi
            exit 0
          fi
        fi
        state="pass=$pass pending=$pending skip=$skip fail=$fail"
        [[ "$state" != "$last" ]] && emit normal "PENDING $state${at:+ at=$at}"
        last="$state"
      fi
    fi

    remaining=$(( TTL - $(elapsed) ))
    if (( remaining <= 0 )); then
      if (( seen )); then
        emit always "TIMEOUT still pending after ${TTL}s${PR_URL:+ $PR_URL}"
        exit 2
      fi
      emit always "NONE no checks reported${PR_URL:+ $PR_URL}"
      exit 5
    fi
    if [[ -n "${WFA_INTERVAL:-}" ]]; then
      nap=$WFA_INTERVAL
    elif (( ! seen || pending == 0 )); then
      nap=5
    else
      nap=$(interval_for "$(elapsed)")
    fi
    (( nap > remaining )) && nap=$remaining
    sleep "$nap"
  done
}

if (( CHECKS || READY )); then
  wait_for_checks
  # Only --ready with a review to wait for gets here: every other outcome exited.
  remaining=$(( TTL - $(elapsed) ))
  if (( remaining <= 0 )); then
    emit always "TIMEOUT CI passed, no time left for the review after ${TTL}s${PR_URL:+ $PR_URL}"
    exit 2
  fi
  [[ -z "$REPO" ]] || export GH_REPO="$REPO"
  run_review "$(review_script)" "$remaining" "$LOG_DIR/review"
fi

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
