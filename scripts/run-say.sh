#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [path/to/file] <min-max>"
  echo "Examples:"
  echo "  $0 lines.txt 1-10"
  echo "  $0 1-10            # defaults to ./lines.txt"
}

if [[ $# -eq 1 ]]; then
  file_path="lines.txt"
  range="$1"
elif [[ $# -eq 2 ]]; then
  file_path="$1"
  range="$2"
else
  usage
  exit 1
fi

if [[ ! -f "$file_path" ]]; then
  echo "Error: File not found: $file_path"
  exit 1
fi

if [[ ! "$range" =~ ^([0-9]+)-([0-9]+)$ ]]; then
  echo "Error: Range must look like min-max (minutes), e.g. 1-10"
  exit 1
fi

min_minutes="${BASH_REMATCH[1]}"
max_minutes="${BASH_REMATCH[2]}"

if (( min_minutes > max_minutes )); then
  echo "Error: min must be <= max"
  exit 1
fi

if ! grep -q '[^[:space:]]' "$file_path"; then
  echo "Error: File has no non-empty lines to speak"
  exit 1
fi

echo "Reading random lines from: $file_path"
echo "Random interval: ${min_minutes}-${max_minutes} minute(s)"
echo "Press Ctrl+C to stop."

while true; do
  line="$(awk 'NF{a[++n]=$0} END{if(n) print a[int(rand()*n)+1]}' "$file_path")"

  if [[ -n "$line" ]]; then
    timestamp="$(date '+%-I:%M %p')"
    echo "[$timestamp]: \"$line\""
    say "$line"
  fi

  sleep_seconds=$(( (RANDOM % (max_minutes - min_minutes + 1) + min_minutes) * 60 ))
  echo "[$(date '+%H:%M:%S')] Sleeping for $((sleep_seconds / 60)) minute(s)..."
  sleep "$sleep_seconds"
done
