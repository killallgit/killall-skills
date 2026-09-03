from pathlib import Path
import re
import unittest


REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "skills"
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
AGENTS = {
    "commenator",
    "git-janitor-investigator",
    "project-planner",
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


def skill_files() -> list[Path]:
    return sorted(SKILLS.glob("*/*/SKILL.md"))


class CatalogLayoutTests(unittest.TestCase):
    """The skills CLI discovers `skills/<category>/<name>/SKILL.md` natively."""

    def test_catalog_holds_exactly_the_expected_domains(self) -> None:
        actual = {path.name for path in SKILLS.iterdir() if path.is_dir()}
        self.assertEqual(actual, set(DOMAINS))

    def test_each_domain_contains_its_exact_skill_inventory(self) -> None:
        for domain, expected in DOMAINS.items():
            actual = {path.name for path in (SKILLS / domain).iterdir() if path.is_dir()}
            self.assertEqual(actual, expected, domain)

    def test_every_skill_sits_at_the_depth_the_cli_walks(self) -> None:
        for path in skill_files():
            self.assertEqual(
                path.relative_to(SKILLS).parts[:-1],
                (path.parent.parent.name, path.parent.name),
            )

    def test_agents_ship_alongside_the_catalog(self) -> None:
        actual = {path.stem for path in (REPO / "agents").glob("*.md")}
        self.assertEqual(actual, AGENTS)


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
                text = (SKILLS / domain / skill / "SKILL.md").read_text()
                for foreign_skill in foreign_skills:
                    self.assertNotIn(f"/{foreign_skill}", text, f"{domain}/{skill}")

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


class DistributionTests(unittest.TestCase):
    """Nothing may point back at the plugin-marketplace era."""

    RETIRED_PATHS = (
        ".claude-plugin",
        ".codex-plugin",
        ".agents/plugins",
        "install.sh",
        "release-please",
        "rules/",
        "hooks/README.md",
    )

    def test_repository_ships_no_plugin_or_release_machinery(self) -> None:
        for name in (
            ".claude-plugin",
            ".agents",
            "plugins",
            "rules",
            "install.sh",
            "release-please-config.json",
            ".release-please-manifest.json",
        ):
            self.assertFalse((REPO / name).exists(), name)

    def test_prose_does_not_reference_retired_distribution_paths(self) -> None:
        for doc in (REPO / "README.md", REPO / "AGENTS.md"):
            text = doc.read_text()
            for retired in self.RETIRED_PATHS:
                self.assertNotIn(retired, text, f"{doc.name} -> {retired}")

    def test_skills_do_not_reference_the_deleted_rules_directory(self) -> None:
        for path in skill_files():
            self.assertNotIn("rules/", path.read_text(), path)

    def test_readme_documents_the_skills_cli_install(self) -> None:
        readme = (REPO / "README.md").read_text()

        for domain in DOMAINS:
            self.assertIn(domain, readme)
        self.assertIn("npx skills", readme)
        self.assertIn("--skill", readme)


if __name__ == "__main__":
    unittest.main()
