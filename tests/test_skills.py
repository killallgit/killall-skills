import json
from pathlib import Path
import re
import unittest


REPO = Path(__file__).resolve().parents[1]
PLUGINS = REPO / "plugins"
MARKETPLACE = REPO / ".agents" / "plugins" / "marketplace.json"
DOMAINS = {
    "planning": {
        "project-planner",
    },
    "engineering": {
        "review-library-usage",
        "git-janitor",
        "wait-for-action",
    },
    "knowledge": {
        "catch-up",
        "matt-pocock",
        "setup-wiki",
        "wiki",
    },
    "experimental": {
        "create-extension",
    },
}
UPSTREAM_SKILLS = {
    "code-review",
    "codebase-design",
    "diagnose",
    "domain-modeling",
    "handoff",
    "improve-codebase-architecture",
    "prototype",
    "research",
    "resolving-merge-conflicts",
    "setup-planning",
    "tdd",
    "to-issues",
    "to-prd",
    "triage",
    "wayfinder",
}
AGENTS = {
    "commenator",
    "git-janitor-investigator",
}
RETIRED_SKILLS = {
    "create-hook",
    "create-rule",
    "create-skill",
    "grill-me",
    "grill-with-docs",
    "grilling",
    "init-project",
    "setup-pre-commit",
    "setup-skills",
    "worktree-cleanup",
    "zoom-out",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def skill_files() -> list[Path]:
    return sorted(PLUGINS.glob("*/skills/*/SKILL.md"))


class CatalogLayoutTests(unittest.TestCase):
    def test_catalog_holds_exactly_the_expected_domain_plugins(self) -> None:
        actual = {path.name for path in PLUGINS.iterdir() if path.is_dir()}
        self.assertEqual(actual, set(DOMAINS))

    def test_each_domain_contains_its_exact_skill_inventory(self) -> None:
        for domain, expected in DOMAINS.items():
            skills = PLUGINS / domain / "skills"
            actual = {path.name for path in skills.iterdir() if path.is_dir()}
            self.assertEqual(actual, expected, domain)

    def test_every_skill_sits_at_the_plugin_discovery_depth(self) -> None:
        for path in skill_files():
            self.assertEqual(
                path.relative_to(PLUGINS).parts[:-1],
                (path.parents[2].name, "skills", path.parent.name),
            )

    def test_agents_ship_alongside_the_catalog(self) -> None:
        actual = {path.stem for path in (REPO / "agents").glob("*.md")}
        self.assertEqual(actual, AGENTS)


class PluginManifestTests(unittest.TestCase):
    def test_marketplace_lists_each_domain_plugin(self) -> None:
        marketplace = load_json(MARKETPLACE)
        entries = {entry["name"]: entry for entry in marketplace["plugins"]}

        self.assertEqual(marketplace["name"], "killallgit")
        self.assertEqual(set(entries), set(DOMAINS))
        for domain, entry in entries.items():
            self.assertEqual(
                entry["source"],
                {"source": "local", "path": f"./plugins/{domain}"},
            )
            self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
            self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")
            self.assertTrue(entry["category"])

    def test_each_domain_has_portable_and_codex_manifests(self) -> None:
        for domain in DOMAINS:
            plugin = PLUGINS / domain
            portable = load_json(plugin / "plugin.json")
            codex = load_json(plugin / ".codex-plugin" / "plugin.json")

            self.assertEqual(
                portable["$schema"],
                "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            )
            self.assertEqual(portable["name"], domain)
            self.assertEqual(codex["name"], domain)
            self.assertEqual(codex["version"], portable["version"])
            self.assertEqual(codex["description"], portable["description"])
            self.assertEqual(codex["skills"], "./skills/")
            self.assertTrue(codex["interface"]["longDescription"])
            self.assertTrue(codex["interface"]["defaultPrompt"])


class SkillFrontmatterTests(unittest.TestCase):
    def test_frontmatter_names_match_directories(self) -> None:
        for path in skill_files():
            match = re.search(r"^name:\s*(\S+)\s*$", path.read_text(), re.M)
            self.assertIsNotNone(match, path)
            self.assertEqual(match.group(1), path.parent.name, path)

    def test_every_skill_declares_a_description(self) -> None:
        for path in skill_files():
            match = re.search(r"^description:\s*(\S.*)$", path.read_text(), re.M)
            self.assertIsNotNone(match, path)


class SkillContentTests(unittest.TestCase):
    def test_domains_do_not_hard_invoke_skills_from_other_domains(self) -> None:
        for domain, skills in DOMAINS.items():
            foreign_skills = set().union(
                *(names for owner, names in DOMAINS.items() if owner != domain)
            )
            for skill in skills:
                text = (PLUGINS / domain / "skills" / skill / "SKILL.md").read_text()
                for foreign_skill in foreign_skills:
                    self.assertNotIn(f"/{foreign_skill}", text, f"{domain}/{skill}")

    def test_upstream_forks_are_absent_and_the_pointer_names_every_one(self) -> None:
        installed = {path.parent.name for path in skill_files()}
        self.assertTrue(UPSTREAM_SKILLS.isdisjoint(installed))

        pointer = PLUGINS / "knowledge" / "skills" / "matt-pocock" / "SKILL.md"
        text = pointer.read_text()
        for skill in UPSTREAM_SKILLS:
            self.assertIn(skill, text, skill)
        self.assertIn("mattpocock/skills", text)

    def test_retired_skills_and_invocations_are_absent(self) -> None:
        installed = {path.parent.name for path in skill_files()}
        self.assertTrue(RETIRED_SKILLS.isdisjoint(installed))

        active_text = "\n".join(path.read_text() for path in skill_files())
        for invocation in (
            "/grilling",
            "/grill-me",
            "/grill-with-docs",
            "/setup-skills",
            "/worktree-cleanup",
            "/zoom-out",
        ):
            self.assertNotIn(invocation, active_text)


class DistributionDocumentationTests(unittest.TestCase):
    def test_readme_documents_both_installation_paths(self) -> None:
        readme = (REPO / "README.md").read_text()

        for domain in DOMAINS:
            self.assertIn(f"{domain}@killallgit", readme)
        self.assertIn("codex plugin marketplace add", readme)
        self.assertIn("npx skills", readme)
        self.assertIn("--skill", readme)

    def test_removed_installer_and_release_files_stay_absent(self) -> None:
        for name in (
            "install.sh",
            "release-please-config.json",
            ".release-please-manifest.json",
        ):
            self.assertFalse((REPO / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
