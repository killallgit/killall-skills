# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
import json
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---", re.DOTALL)


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    hooks: dict | None = None


def parse_skill(text: str) -> Skill:
    match = FRONTMATTER.match(text)
    if match is None:
        raise ValueError("SKILL.md has no frontmatter")
    fields = yaml.safe_load(match.group(1)) or {}
    if not fields.get("name") or not fields.get("description"):
        raise ValueError("frontmatter needs name and description")
    return Skill(fields["name"], " ".join(fields["description"].split()))


def read_skills(skills_dir: Path) -> tuple[Skill, ...]:
    skills = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        skill = parse_skill(skill_md.read_text())
        if skill.name != skill_md.parent.name:
            raise ValueError(f"{skill_md.parent.name} declares name {skill.name}")
        hooks_file = skill_md.parent / "hooks" / "hooks.json"
        hooks = json.loads(hooks_file.read_text())["hooks"] if hooks_file.exists() else None
        skills.append(replace(skill, hooks=hooks))
    return tuple(skills)


def skill_path(skill: Skill) -> str:
    return f"./skills/{skill.name}"


def merge_hooks(hook_sets: list[dict]) -> dict:
    merged: dict[str, list] = {}
    for hooks in hook_sets:
        for event, matchers in hooks.items():
            merged[event] = [*merged.get(event, []), *matchers]
    return merged


def build_entry(
    config: dict,
    name: str,
    description: str,
    paths: list[str],
    hooks: dict | None,
) -> dict:
    entry = {
        "name": name,
        "source": "./",
        "description": description,
        "strict": False,
        "skills": paths,
        "category": config["category"],
        "homepage": config["homepage"],
    }
    optional = {"version": config.get("version"), "hooks": hooks}
    return {**entry, **{key: value for key, value in optional.items() if value}}


def build_marketplace(config: dict, skills: tuple[Skill, ...]) -> dict:
    bundle = build_entry(
        config,
        config["bundle"]["name"],
        config["bundle"]["description"],
        [skill_path(skill) for skill in skills],
        merge_hooks([skill.hooks for skill in skills if skill.hooks]),
    )
    singles = [
        build_entry(
            config, skill.name, skill.description, [skill_path(skill)], skill.hooks
        )
        for skill in skills
    ]
    return {
        "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
        "name": config["name"],
        "description": config["description"],
        "owner": config["owner"],
        "plugins": [bundle, *singles],
    }


def render(data: dict) -> str:
    return json.dumps(data, indent=2) + "\n"


def generated_files(root: Path) -> dict[Path, str]:
    config = json.loads((root / "marketplace.config.json").read_text())
    skills = read_skills(root / "skills")
    return {
        root / ".claude-plugin" / "marketplace.json": render(
            build_marketplace(config, skills)
        ),
    }


def drifted_files(files: dict[Path, str]) -> list[Path]:
    return [
        path
        for path, content in files.items()
        if not path.exists() or path.read_text() != content
    ]


def write_files(files: dict[Path, str]) -> None:
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def main(argv: list[str]) -> int:
    files = generated_files(Path(__file__).resolve().parent.parent)
    if "--check" not in argv:
        write_files(files)
        return 0
    drifted = drifted_files(files)
    for path in drifted:
        print(f"out of date: {path.name}", file=sys.stderr)
    return 1 if drifted else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
