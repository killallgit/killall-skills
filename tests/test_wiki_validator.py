import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def load_module(name, relative_path):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wiki_setup = load_module(
    "wiki_setup_for_validator",
    "payload/skills/setup-wiki/scripts/wiki_setup.py",
)
wiki_check = load_module(
    "wiki_check",
    "payload/skills/setup-wiki/scripts/wiki_check.py",
)


class WikiValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.projects_root = Path(self.temporary.name)
        self.project = self.projects_root / "api"
        self.project.mkdir()
        self.vault = self.projects_root / "platform-wiki"
        wiki_setup.scaffold_vault(
            self.vault,
            "platform",
            "Explain the platform.",
            [self.project],
            [],
        )
        source = self.vault / "raw" / "source.md"
        source.write_text("# Source\n")
        (self.vault / "raw" / "manifest.jsonl").write_text(
            json.dumps(
                {
                    "id": "source-1",
                    "path": "raw/source.md",
                    "sha256": "a" * 64,
                    "acquired_at": "2026-07-30",
                    "sensitivity": "internal",
                }
            )
            + "\n"
        )
        self.write_claims(
            [
                {
                    "id": "claim-1",
                    "statement": "API depends on the shared database.",
                    "source_ids": ["source-1"],
                    "status": "verified",
                    "observed_at": "2026-07-30",
                    "predicate": "depends_on",
                }
            ]
        )

    def tearDown(self):
        self.temporary.cleanup()

    def write_claims(self, claims):
        (self.vault / "claims" / "claims.jsonl").write_text(
            "".join(json.dumps(claim) + "\n" for claim in claims)
        )

    def test_accepts_valid_scaffold_and_claim_graph(self):
        result = wiki_check.check_vault(self.vault)

        self.assertEqual(result.errors, ())

    def test_rejects_duplicate_claim_ids(self):
        claim = {
            "id": "claim-1",
            "statement": "API depends on the shared database.",
            "source_ids": ["source-1"],
            "status": "verified",
            "observed_at": "2026-07-30",
            "predicate": "depends_on",
        }
        self.write_claims([claim, claim])

        result = wiki_check.check_vault(self.vault)

        self.assertIn("duplicate claim id: claim-1", result.errors)

    def test_rejects_missing_claim_source(self):
        self.write_claims(
            [
                {
                    "id": "claim-2",
                    "statement": "A source is missing.",
                    "source_ids": ["source-missing"],
                    "status": "candidate",
                    "observed_at": "2026-07-30",
                }
            ]
        )

        result = wiki_check.check_vault(self.vault)

        self.assertIn(
            "claim claim-2 references missing source: source-missing",
            result.errors,
        )

    def test_rejects_reversed_temporal_interval(self):
        self.write_claims(
            [
                {
                    "id": "claim-3",
                    "statement": "The interval is reversed.",
                    "source_ids": ["source-1"],
                    "status": "superseded",
                    "observed_at": "2026-07-30",
                    "valid_from": "2026-07-30",
                    "valid_to": "2026-07-01",
                }
            ]
        )

        result = wiki_check.check_vault(self.vault)

        self.assertIn(
            "claim claim-3 has valid_to before valid_from",
            result.errors,
        )

    def test_rejects_missing_wikilink_target(self):
        (self.vault / "wiki" / "concepts" / "broken.md").write_text(
            "# Broken\n\nSee [[absent-page]].\n"
        )

        result = wiki_check.check_vault(self.vault)

        self.assertIn(
            "wiki/concepts/broken.md links to missing page: absent-page",
            result.errors,
        )

    def test_rejects_predicate_outside_ontology(self):
        self.write_claims(
            [
                {
                    "id": "claim-4",
                    "statement": "The predicate is not accepted.",
                    "source_ids": ["source-1"],
                    "status": "candidate",
                    "observed_at": "2026-07-30",
                    "predicate": "invented_relation",
                }
            ]
        )

        result = wiki_check.check_vault(self.vault)

        self.assertIn(
            "claim claim-4 uses unknown predicate: invented_relation",
            result.errors,
        )


if __name__ == "__main__":
    unittest.main()
