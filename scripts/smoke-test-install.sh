#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

info() {
  echo "==> $*"
}

extract_name() {
  awk '
    BEGIN { in_frontmatter = 0 }
    NR == 1 {
      if ($0 != "---") {
        exit 1
      }
      in_frontmatter = 1
      next
    }
    in_frontmatter && $0 == "---" { exit }
    in_frontmatter && /^name:[[:space:]]*/ {
      sub(/^name:[[:space:]]*/, "", $0)
      print
      exit
    }
  ' "$1"
}

extract_description() {
  awk '
    BEGIN {
      in_frontmatter = 0
      collecting = 0
      description = ""
    }
    NR == 1 {
      if ($0 != "---") {
        exit 1
      }
      in_frontmatter = 1
      next
    }
    in_frontmatter && $0 == "---" {
      if (collecting) {
        print description
      }
      exit
    }
    !in_frontmatter {
      next
    }
    collecting {
      if ($0 ~ /^[^[:space:]]/) {
        print description
        exit
      }
      gsub(/^[[:space:]]+/, "", $0)
      if ($0 == "") {
        next
      }
      if (description != "") {
        description = description " "
      }
      description = description $0
      next
    }
    /^description:[[:space:]]*[>|][+-]?[[:space:]]*$/ {
      collecting = 1
      next
    }
    /^description:[[:space:]]*/ {
      sub(/^description:[[:space:]]*/, "", $0)
      print
      exit
    }
  ' "$1"
}

check_versions() {
  local claude_version codex_version

  claude_version="$(jq -r .version "$REPO_ROOT/.claude-plugin/plugin.json")"
  codex_version="$(jq -r .version "$REPO_ROOT/.codex-plugin/plugin.json")"

  [[ "$claude_version" == "$codex_version" ]] || fail "plugin versions differ: Claude=$claude_version Codex=$codex_version"
  info "plugin versions are in sync: $claude_version"
}

check_skills() {
  local skill_file skill_name skill_description

  for skill_file in "$REPO_ROOT"/skills/*/SKILL.md; do
    skill_name="$(extract_name "$skill_file")"
    skill_description="$(extract_description "$skill_file")"

    [[ -n "$skill_name" ]] || fail "$skill_file is missing a name"
    [[ -n "$skill_description" ]] || fail "$skill_file is missing a description"
  done

  info "all skills have name and description frontmatter"
}

check_commands() {
  local command_file description

  for command_file in "$REPO_ROOT"/commands/*.md; do
    description="$(extract_description "$command_file")"
    [[ -n "$description" ]] || fail "$command_file is missing command frontmatter"
  done

  info "all commands have frontmatter"
}

smoke_claude() {
  local home_dir

  if ! command -v claude >/dev/null 2>&1; then
    info "skipping Claude smoke test; claude is not installed"
    return
  fi

  home_dir="$TMP_ROOT/claude-home"
  mkdir -p "$home_dir/.config"

  claude plugin validate "$REPO_ROOT" >/dev/null
  HOME="$home_dir" XDG_CONFIG_HOME="$home_dir/.config" claude plugin marketplace add "$REPO_ROOT" >/dev/null
  HOME="$home_dir" XDG_CONFIG_HOME="$home_dir/.config" claude plugin install killall-skills@killallgit --scope user >/dev/null

  [[ -f "$home_dir/.claude/settings.json" ]] || fail "Claude smoke test did not produce user settings"
  info "Claude marketplace add/install smoke test passed"
}

smoke_codex() {
  local home_dir

  if ! command -v codex >/dev/null 2>&1; then
    info "skipping Codex smoke test; codex is not installed"
    return
  fi

  home_dir="$TMP_ROOT/codex-home"
  mkdir -p "$home_dir/.config"

  HOME="$home_dir" XDG_CONFIG_HOME="$home_dir/.config" codex plugin marketplace add "$REPO_ROOT" >/dev/null
  info "Codex marketplace add smoke test passed"
}

smoke_cursor_export() {
  local target_dir expected_rules actual_rules

  target_dir="$TMP_ROOT/cursor-target"
  mkdir -p "$target_dir"

  bash "$REPO_ROOT/scripts/export-cursor-rules.sh" "$target_dir" >/dev/null

  expected_rules="$(find "$REPO_ROOT/skills" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
  actual_rules="$(find "$target_dir/.cursor/rules" -name 'killall-*.mdc' | wc -l | tr -d ' ')"

  [[ "$actual_rules" == "$expected_rules" ]] || fail "expected $expected_rules Cursor rules, found $actual_rules"
  [[ -f "$target_dir/.cursor/killall-skills/skills/wait-for-action/wait-for.sh" ]] || fail "Cursor export did not copy skill assets"
  info "Cursor export smoke test passed"
}

check_versions
check_skills
check_commands
smoke_claude
smoke_codex
smoke_cursor_export

info "all packaging smoke tests passed"
