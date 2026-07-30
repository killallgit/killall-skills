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


if __name__ == "__main__":
    unittest.main()
