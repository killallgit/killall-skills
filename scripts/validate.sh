#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

info() {
  echo "==> $*"
}

extract_frontmatter_field() {
  local field="$1"
  local file="$2"

  awk -v field="$field" '
    BEGIN { in_frontmatter = 0 }
    NR == 1 {
      if ($0 != "---") {
        exit 1
      }
      in_frontmatter = 1
      next
    }
    in_frontmatter && $0 == "---" { exit }
    in_frontmatter && index($0, field ":") == 1 {
      sub("^[^:]+:[[:space:]]*", "", $0)
      print
      exit
    }
  ' "$file"
}

check_no_tool_specific_surfaces() {
  local matches

  matches="$(
    find "$REPO_ROOT" \
      -path "$REPO_ROOT/.git" -prune -o \
      \( \
        -name marketplace.json -o \
        -name plugin.json -o \
        -name '.github' -o \
        -name commands -o \
        -name plugins \
      \) -print
  )"

  [[ -z "$matches" ]] || fail "host-specific packaging surfaces remain:
$matches"

  info "no host-specific packaging surfaces found"
}

check_skills() {
  local skill_file skill_name skill_description

  [[ -f "$REPO_ROOT/payload/README.md" ]] || fail "missing payload/README.md"
  [[ -d "$REPO_ROOT/payload/skills" ]] || fail "missing payload/skills"
  [[ -d "$REPO_ROOT/payload/rules" ]] || fail "missing payload/rules"

  for skill_file in "$REPO_ROOT"/payload/skills/*/SKILL.md; do
    [[ -f "$skill_file" ]] || continue
    skill_name="$(extract_frontmatter_field name "$skill_file")"
    skill_description="$(extract_frontmatter_field description "$skill_file")"

    [[ -n "$skill_name" ]] || fail "$skill_file is missing a name"
    [[ -n "$skill_description" ]] || fail "$skill_file is missing a description"
  done

  info "all skills have name and description frontmatter"
}

check_hooks() {
  local phase hook_file

  [[ -f "$REPO_ROOT/payload/hooks/README.md" ]] || fail "missing payload/hooks/README.md"

  for phase in pre-session pre-tool post-tool post-session; do
    [[ -d "$REPO_ROOT/payload/hooks/$phase" ]] || fail "missing payload/hooks/$phase"
    [[ -f "$REPO_ROOT/payload/hooks/$phase/README.md" ]] || fail "missing payload/hooks/$phase/README.md"
  done

  while IFS= read -r hook_file; do
    [[ -x "$hook_file" ]] || fail "hook is not executable: ${hook_file#$REPO_ROOT/}"
    bash -n "$hook_file" || fail "hook has invalid syntax: ${hook_file#$REPO_ROOT/}"
  done < <(find "$REPO_ROOT/payload/hooks" -type f -name '*.sh' | LC_ALL=C sort)

  info "hook tree is valid"
}

check_no_tool_specific_references() {
  local matches

  matches="$(
    grep -RInE 'marketplace|plugin manifest' \
      "$REPO_ROOT/README.md" "$REPO_ROOT/AGENTS.md" "$REPO_ROOT/payload/hooks" 2>/dev/null || true
  )"

  [[ -z "$matches" ]] || fail "host-specific packaging references remain in top-level docs/hooks:
$matches"

  info "top-level docs, hooks, and scripts are host-neutral"
}

check_no_tool_specific_surfaces
check_skills
check_hooks
check_no_tool_specific_references

info "validation passed"
