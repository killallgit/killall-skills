import json
from pathlib import Path
import re
import unittest


REPO = Path(__file__).resolve().parents[1]
DOMAINS = {
    "planning": {
        "project-planner",
        "setup-planning",
        "to-prd",
        "to-issues",
        "triage",
        "wayfinder",
    },
    "engineering": {
        "tdd",
        "diagnose",
        "code-review",
        "review-library-usage",
        "resolving-merge-conflicts",
        "git-janitor",
        "wait-for-action",
        "record",
    },
    "architecture": {
        "domain-modeling",
        "codebase-design",
        "improve-codebase-architecture",
    },
    "knowledge": {
        "research",
        "setup-wiki",
        "wiki",
        "handoff",
    },
    "experimental": {
        "prototype",
        "create-extension",
    },
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


class PluginManifestTests(unittest.TestCase):
    def test_claude_marketplace_lists_each_domain_plugin(self) -> None:
        marketplace = load_json(REPO / ".claude-plugin" / "marketplace.json")
        entries = {entry["name"]: entry for entry in marketplace["plugins"]}

        self.assertEqual(set(entries), set(DOMAINS))
        for domain, entry in entries.items():
            self.assertEqual(entry["source"], f"./plugins/{domain}")

    def test_codex_marketplace_lists_each_domain_plugin(self) -> None:
        marketplace = load_json(REPO / ".agents" / "plugins" / "marketplace.json")
        entries = {entry["name"]: entry for entry in marketplace["plugins"]}

        self.assertEqual(set(entries), set(DOMAINS))
        for domain, entry in entries.items():
            self.assertEqual(
                entry["source"],
                {"source": "local", "path": f"./plugins/{domain}"},
            )
            self.assertEqual(entry["policy"]["installation"], "AVAILABLE")

    def test_each_domain_has_matching_host_manifests(self) -> None:
        for domain in DOMAINS:
            plugin = REPO / "plugins" / domain
            claude = load_json(plugin / ".claude-plugin" / "plugin.json")
            codex = load_json(plugin / ".codex-plugin" / "plugin.json")

            self.assertEqual(claude["name"], domain)
            self.assertEqual(codex["name"], domain)
            self.assertEqual(claude["version"], "0.5.0")
            self.assertEqual(codex["version"], "0.5.0")
            self.assertEqual(codex["skills"], "./skills/")
            self.assertTrue(codex["interface"]["longDescription"])
            self.assertGreater(len(codex["interface"]["defaultPrompt"]), 0)


class PluginInventoryTests(unittest.TestCase):
    def test_each_domain_contains_its_exact_skill_inventory(self) -> None:
        plugin_directories = {
            path.name for path in (REPO / "plugins").iterdir() if path.is_dir()
        }
        self.assertEqual(plugin_directories, set(DOMAINS))

        for domain, expected in DOMAINS.items():
            skills_root = REPO / "plugins" / domain / "skills"
            actual = {path.name for path in skills_root.iterdir() if path.is_dir()}
            self.assertEqual(actual, expected, domain)

    def test_domains_do_not_hard_invoke_skills_from_other_plugins(self) -> None:
        for domain, skills in DOMAINS.items():
            foreign_skills = set().union(
                *(names for owner, names in DOMAINS.items() if owner != domain)
            )
            for skill in skills:
                text = (
                    REPO / "plugins" / domain / "skills" / skill / "SKILL.md"
                ).read_text()
                for foreign_skill in foreign_skills:
                    self.assertNotIn(f"/{foreign_skill}", text, f"{domain}/{skill}")

    def test_skill_frontmatter_names_match_directories(self) -> None:
        for domain in DOMAINS:
            for skill_file in (REPO / "plugins" / domain / "skills").glob(
                "*/SKILL.md"
            ):
                match = re.search(r"^name:\s*(\S+)\s*$", skill_file.read_text(), re.M)
                self.assertIsNotNone(match, skill_file)
                self.assertEqual(match.group(1), skill_file.parent.name, skill_file)

    def test_retired_skills_and_invocations_are_absent(self) -> None:
        skill_files = list((REPO / "plugins").glob("*/skills/*/SKILL.md"))
        installed_names = {path.parent.name for path in skill_files}
        self.assertTrue(RETIRED_SKILLS.isdisjoint(installed_names))

        active_text = "\n".join(path.read_text() for path in skill_files)
        for invocation in (
            "/grilling",
            "/grill-me",
            "/grill-with-docs",
            "/setup-skills",
            "/worktree-cleanup",
            "/zoom-out",
        ):
            self.assertNotIn(invocation, active_text)


class PluginDocumentationTests(unittest.TestCase):
    def test_readme_documents_current_domain_installation(self) -> None:
        readme = (REPO / "README.md").read_text()

        for domain in DOMAINS:
            self.assertIn(domain, readme)
        self.assertIn("--skill", readme)
        self.assertNotIn("killall-skills@killallgit", readme)
        self.assertNotIn("payload/skills", readme)
        self.assertNotIn("payload/agents", readme)


if __name__ == "__main__":
    unittest.main()
