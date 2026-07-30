import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).parents[1]
    / "payload"
    / "skills"
    / "setup-wiki"
    / "scripts"
    / "wiki_setup.py"
)
SPEC = importlib.util.spec_from_file_location("wiki_setup", MODULE_PATH)
wiki_setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wiki_setup)


class WikiScaffoldTests(unittest.TestCase):
    def test_scaffolds_shared_vault_and_project_pointers(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp)
            api = projects_root / "api"
            web = projects_root / "web"
            api.mkdir()
            web.mkdir()
            vault = projects_root / "platform-wiki"

            result = wiki_setup.scaffold_vault(
                vault=vault,
                name="platform",
                purpose="Explain how the platform projects fit together.",
                projects=[api, web],
                excludes=["**/.env", "**/dist/**"],
            )

            config = json.loads((vault / "wiki.json").read_text())
            self.assertEqual(config["name"], "platform")
            self.assertEqual(
                config["projects"],
                [str(api.resolve()), str(web.resolve())],
            )
            self.assertEqual(config["excludes"], ["**/.env", "**/dist/**"])
            self.assertEqual(
                json.loads((api / ".wiki.json").read_text())["vault"],
                str(vault.resolve()),
            )
            self.assertEqual(
                json.loads((web / ".wiki.json").read_text())["vault"],
                str(vault.resolve()),
            )
            self.assertTrue((vault / "ontology" / "schema.yaml").is_file())
            self.assertTrue((vault / "queues" / "contradictions").is_dir())
            self.assertIn(vault.resolve() / "wiki.json", result.created)
            self.assertEqual(
                result.pointers,
                (api.resolve() / ".wiki.json", web.resolve() / ".wiki.json"),
            )

    def test_rerun_preserves_user_edited_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp)
            project = projects_root / "api"
            project.mkdir()
            vault = projects_root / "platform-wiki"
            wiki_setup.scaffold_vault(
                vault,
                "platform",
                "Explain the platform.",
                [project],
                [],
            )
            overview = vault / "wiki" / "overview.md"
            overview.write_text("# Curated overview\n")

            result = wiki_setup.scaffold_vault(
                vault,
                "platform",
                "Explain the platform.",
                [project],
                [],
            )

            self.assertEqual(overview.read_text(), "# Curated overview\n")
            self.assertIn(overview.resolve(), result.preserved)

    def test_rejects_project_pointer_to_another_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp)
            project = projects_root / "api"
            project.mkdir()
            (project / ".wiki.json").write_text(
                json.dumps({"vault": str(projects_root / "other-wiki")})
            )

            with self.assertRaisesRegex(ValueError, "already points to another vault"):
                wiki_setup.scaffold_vault(
                    projects_root / "platform-wiki",
                    "platform",
                    "Explain the platform.",
                    [project],
                    [],
                )

    def test_generated_contract_exposes_runtime_workflows(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp)
            project = projects_root / "api"
            project.mkdir()
            vault = projects_root / "platform-wiki"

            wiki_setup.scaffold_vault(
                vault,
                "platform",
                "Explain the platform.",
                [project],
                ["**/.env"],
            )

            config = json.loads((vault / "wiki.json").read_text())
            self.assertEqual(config["layers"]["sources"], "raw")
            self.assertEqual(config["layers"]["compiled"], "wiki")
            self.assertEqual(config["layers"]["claims"], "claims")
            self.assertEqual(config["layers"]["ontology"], "ontology")
            self.assertEqual(
                set(config["workflows"]),
                {"ingest", "query", "lint", "evaluate", "ontology", "journal"},
            )
            self.assertEqual(
                config["review_required"],
                [
                    "new_claim",
                    "contradiction",
                    "entity_merge",
                    "destructive_change",
                    "ontology_change",
                ],
            )
            self.assertEqual(
                config["commands"]["validator"],
                "python3 scripts/wiki-check.py .",
            )
            self.assertEqual(config["entry_points"]["operations"], "WIKI-OPERATIONS.md")
            self.assertEqual(config["entry_points"]["session_context"], "KNOWLEDGE.md")

    def test_records_confirmed_setup_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp)
            project = projects_root / "api"
            project.mkdir()
            vault = projects_root / "platform-wiki"

            wiki_setup.scaffold_vault(
                vault,
                "platform",
                "Explain the platform.",
                [project],
                [],
                options={
                    "audience": "team",
                    "git_policy": "reviewed",
                    "retrieval": "qmd",
                    "sensitivity": "internal",
                },
            )

            config = json.loads((vault / "wiki.json").read_text())
            self.assertEqual(
                config["options"],
                {
                    "audience": "team",
                    "git_policy": "reviewed",
                    "retrieval": "qmd",
                    "sensitivity": "internal",
                },
            )


if __name__ == "__main__":
    unittest.main()
