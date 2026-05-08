#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/export-cursor-rules.sh /path/to/target-repo

Copies killall-skills into a target repository as Cursor project rules.
Generated rules land in:
  .cursor/rules/killall-*.mdc

Supporting skill files land in:
  .cursor/killall-skills/skills/
EOF
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
      print $0
      exit
    }
  ' "$1"
}

yaml_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

if [[ $# -ne 1 ]]; then
  usage >&2
  exit 1
fi

if [[ ! -d "$1" ]]; then
  echo "Target repo does not exist: $1" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_ROOT="$(cd "$1" && pwd)"
CURSOR_ROOT="$TARGET_ROOT/.cursor"
RULES_ROOT="$CURSOR_ROOT/rules"
ASSETS_ROOT="$CURSOR_ROOT/killall-skills"
SKILLS_SRC="$REPO_ROOT/skills"

mkdir -p "$RULES_ROOT" "$ASSETS_ROOT"
rm -rf "$ASSETS_ROOT/skills"
cp -R "$SKILLS_SRC" "$ASSETS_ROOT/skills"
rm -f "$RULES_ROOT"/killall-*.mdc

count=0
for skill_dir in "$SKILLS_SRC"/*; do
  [[ -d "$skill_dir" ]] || continue

  skill_name="$(basename "$skill_dir")"
  skill_file="$skill_dir/SKILL.md"
  description="$(extract_description "$skill_file")"

  if [[ -z "$description" ]]; then
    echo "Missing description in $skill_file" >&2
    exit 1
  fi

  rule_file="$RULES_ROOT/killall-$skill_name.mdc"
  {
    printf -- '---\n'
    printf 'description: "%s"\n' "$(yaml_escape "$description")"
    printf -- '---\n\n'
    printf '# killall-skills: %s\n\n' "$skill_name"
    printf 'Imported from the `killall-skills` repository. This is an agent-requested Cursor project rule that mirrors the source skill and its companion files.\n\n'
    printf '@../killall-skills/skills/%s/SKILL.md\n' "$skill_name"

    while IFS= read -r asset_file; do
      rel_path="${asset_file#$skill_dir/}"
      printf '@../killall-skills/skills/%s/%s\n' "$skill_name" "$rel_path"
    done < <(find "$skill_dir" -type f ! -name SKILL.md | LC_ALL=C sort)
  } > "$rule_file"

  count=$((count + 1))
done

printf 'Exported %d Cursor rules to %s\n' "$count" "$RULES_ROOT"
printf 'Copied skill assets to %s\n' "$ASSETS_ROOT/skills"
