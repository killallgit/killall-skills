import json
from pathlib import Path

import pytest

from generate_manifests import (
    Skill,
    build_copilot_marketplace,
    build_cursor_marketplace,
    build_marketplace,
    drifted_files,
    generated_files,
    parse_skill,
    read_skills,
    write_files,
)

CONFIG = {
    "name": "mkt",
    "description": "marketplace",
    "owner": {"name": "owner"},
    "homepage": "https://example.test",
    "category": "workflow",
    "bundle": {"name": "bundle", "description": "all"},
}
SKILLS = (Skill("alpha", "first"), Skill("beta", "second"))


def write_skill(root: Path, dirname: str, frontmatter: str) -> None:
    skill_dir = root / "skills" / dirname
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n\n# body\n")


def write_repo(root: Path) -> None:
    write_skill(root, "alpha", "name: alpha\ndescription: first")
    scripts = root / "scripts"
    scripts.mkdir()
    (scripts / "marketplace.config.json").write_text(json.dumps(CONFIG))


def test_parse_skill_reads_plain_description():
    skill = parse_skill("---\nname: alpha\ndescription: first\n---\nbody")

    assert skill == Skill("alpha", "first")


def test_parse_skill_joins_folded_description_into_one_line():
    text = "---\nname: alpha\ndescription: >\n  one\n  two\n---\nbody"

    assert parse_skill(text).description == "one two"


def test_parse_skill_without_frontmatter_raises():
    with pytest.raises(ValueError):
        parse_skill("# no frontmatter")


def test_parse_skill_missing_description_raises():
    with pytest.raises(ValueError):
        parse_skill("---\nname: alpha\n---\nbody")


def test_read_skills_returns_skills_sorted_by_name(tmp_path):
    write_skill(tmp_path, "beta", "name: beta\ndescription: second")
    write_skill(tmp_path, "alpha", "name: alpha\ndescription: first")

    assert read_skills(tmp_path / "skills") == SKILLS


def test_read_skills_rejects_name_that_differs_from_directory(tmp_path):
    write_skill(tmp_path, "alpha", "name: other\ndescription: first")

    with pytest.raises(ValueError):
        read_skills(tmp_path / "skills")


def test_marketplace_lists_each_skill_then_bundle():
    plugins = build_marketplace(CONFIG, SKILLS)["plugins"]

    assert [p["name"] for p in plugins] == ["alpha", "beta", "bundle"]


def test_skills_cli_last_matching_plugin_groups_every_skill_under_bundle():
    plugins = build_marketplace(CONFIG, SKILLS)["plugins"]
    groups = {
        path: plugin["name"]
        for plugin in plugins
        for path in plugin["skills"]
    }

    assert groups == {"./skills/alpha": "bundle", "./skills/beta": "bundle"}


def test_bundle_entry_exposes_every_skill_path():
    bundle = build_marketplace(CONFIG, SKILLS)["plugins"][-1]

    assert bundle["skills"] == ["./skills/alpha", "./skills/beta"]


def test_skill_entry_exposes_only_its_own_path():
    alpha = build_marketplace(CONFIG, SKILLS)["plugins"][0]

    assert alpha["skills"] == ["./skills/alpha"]


def test_every_entry_is_loaded_from_repo_root_without_a_manifest():
    plugins = build_marketplace(CONFIG, SKILLS)["plugins"]

    assert {(p["source"], p["strict"]) for p in plugins} == {("./", False)}


def test_marketplace_entries_carry_no_version():
    plugins = build_marketplace(CONFIG, SKILLS)["plugins"]

    assert all("version" not in p for p in plugins)


def test_skill_entry_description_comes_from_frontmatter():
    alpha = build_marketplace(CONFIG, SKILLS)["plugins"][0]

    assert alpha["description"] == "first"


def test_generated_files_cover_claude_cursor_and_copilot(tmp_path):
    write_repo(tmp_path)

    assert set(generated_files(tmp_path)) == {
        tmp_path / ".claude-plugin" / "marketplace.json",
        tmp_path / ".cursor-plugin" / "marketplace.json",
        tmp_path / ".github" / "plugin" / "marketplace.json",
        tmp_path / "skills" / "alpha" / ".cursor-plugin" / "plugin.json",
        tmp_path / "skills" / ".cursor-plugin" / "plugin.json",
    }


def catalog(tmp_path, relative):
    return json.loads(generated_files(tmp_path)[tmp_path / relative])


def test_cursor_catalog_points_each_plugin_at_its_skill_directory(tmp_path):
    write_repo(tmp_path)
    write_skill(tmp_path, "beta", "name: beta\ndescription: second")
    plugins = catalog(tmp_path, ".cursor-plugin/marketplace.json")["plugins"]

    assert [(p["name"], p["source"]) for p in plugins] == [
        ("alpha", "./skills/alpha"),
        ("beta", "./skills/beta"),
        ("bundle", "./skills"),
    ]
    assert all("strict" not in p for p in plugins)
    assert all("skills" not in p for p in plugins[:-1])
    assert plugins[-1]["skills"] == ["./alpha", "./beta"]


def test_cursor_sources_have_manifests_and_discover_every_skill(tmp_path):
    write_repo(tmp_path)
    write_skill(tmp_path, "beta", "name: beta\ndescription: second")
    write_files(generated_files(tmp_path))
    marketplace = json.loads((tmp_path / ".cursor-plugin" / "marketplace.json").read_text())

    for plugin in marketplace["plugins"]:
        source = tmp_path / plugin["source"]
        manifest = json.loads((source / ".cursor-plugin" / "plugin.json").read_text())
        assert manifest["name"] == plugin["name"]
        assert manifest["description"] == plugin["description"]
        if plugin["name"] == "bundle":
            assert manifest["skills"] == ["./alpha", "./beta"]
            assert all((source / path / "SKILL.md").is_file() for path in manifest["skills"])
        else:
            assert "skills" not in manifest
            assert not (source / "skills").exists()
            assert (source / "SKILL.md").is_file()


def test_cursor_manifests_inherit_version_from_the_marketplace(tmp_path):
    write_repo(tmp_path)
    config_path = tmp_path / "scripts" / "marketplace.config.json"
    config_path.write_text(json.dumps({**CONFIG, "version": "1.2.3"}))
    files = generated_files(tmp_path)
    marketplace = json.loads(files[tmp_path / ".cursor-plugin" / "marketplace.json"])

    for plugin in marketplace["plugins"]:
        manifest = json.loads(files[tmp_path / plugin["source"] / ".cursor-plugin" / "plugin.json"])
        assert plugin["version"] == "1.2.3"
        assert "version" not in manifest


def test_copilot_catalog_selects_skills_from_the_repo_root(tmp_path):
    write_repo(tmp_path)
    write_skill(tmp_path, "beta", "name: beta\ndescription: second")
    marketplace = catalog(tmp_path, ".github/plugin/marketplace.json")

    assert marketplace["metadata"]["description"] == CONFIG["description"]
    assert [p["skills"] for p in marketplace["plugins"]] == [
        ["./skills/alpha"],
        ["./skills/beta"],
        ["./skills/alpha", "./skills/beta"],
    ]
    assert {(p["source"], p["strict"]) for p in marketplace["plugins"]} == {("./", False)}


def test_drifted_files_is_empty_after_write(tmp_path):
    write_repo(tmp_path)
    files = generated_files(tmp_path)
    write_files(files)

    assert drifted_files(files) == []


def test_drifted_files_reports_stale_file(tmp_path):
    write_repo(tmp_path)
    files = generated_files(tmp_path)
    write_files(files)
    marketplace = tmp_path / ".claude-plugin" / "marketplace.json"
    marketplace.write_text("{}")

    assert drifted_files(files) == [marketplace]


def test_drifted_files_reports_missing_file(tmp_path):
    write_repo(tmp_path)
    files = generated_files(tmp_path)

    assert drifted_files(files) == list(files)


def test_version_from_config_is_set_on_every_entry():
    config = {**CONFIG, "version": "1.2.3"}
    plugins = build_marketplace(config, SKILLS)["plugins"]

    assert {p["version"] for p in plugins} == {"1.2.3"}


ALPHA_HOOKS = {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "a"}]}]}
BETA_HOOKS = {
    "PreToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": "b"}]}],
    "Stop": [{"hooks": [{"type": "command", "command": "c"}]}],
}


def test_skill_with_hooks_inlines_them_in_its_entry():
    hooked = (Skill("alpha", "first", hooks=ALPHA_HOOKS), SKILLS[1])
    plugins = build_marketplace(CONFIG, hooked)["plugins"]

    assert plugins[0]["hooks"] == ALPHA_HOOKS


def test_bundle_merges_the_hooks_of_every_skill_by_event():
    hooked = (Skill("alpha", "first", hooks=ALPHA_HOOKS), Skill("beta", "second", hooks=BETA_HOOKS))
    bundle = build_marketplace(CONFIG, hooked)["plugins"][-1]

    assert bundle["hooks"] == {
        "PreToolUse": ALPHA_HOOKS["PreToolUse"] + BETA_HOOKS["PreToolUse"],
        "Stop": BETA_HOOKS["Stop"],
    }


def test_copilot_entries_keep_hooks_and_cursor_entries_leave_them_in_the_skill():
    hooked = (Skill("alpha", "first", hooks=ALPHA_HOOKS), SKILLS[1])

    copilot = build_copilot_marketplace(CONFIG, hooked)["plugins"]
    cursor = build_cursor_marketplace(CONFIG, hooked)["plugins"]

    assert copilot[0]["hooks"] == ALPHA_HOOKS
    assert all("hooks" not in plugin for plugin in cursor)


def test_entries_without_hooks_have_no_hooks_key():
    plugins = build_marketplace(CONFIG, SKILLS)["plugins"]

    assert all("hooks" not in p for p in plugins)


def test_read_skills_loads_the_hooks_of_a_skill(tmp_path):
    write_skill(tmp_path, "alpha", "name: alpha\ndescription: first")
    hooks_dir = tmp_path / "skills" / "alpha" / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "hooks.json").write_text(json.dumps({"hooks": ALPHA_HOOKS}))

    assert read_skills(tmp_path / "skills")[0].hooks == ALPHA_HOOKS
