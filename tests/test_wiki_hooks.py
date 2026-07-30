import importlib.util
import json
import subprocess
import sys
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
    "wiki_setup_for_hooks",
    "payload/skills/setup-wiki/scripts/wiki_setup.py",
)
hook_installer = load_module(
    "wiki_hook_installer",
    "payload/skills/setup-wiki/scripts/install-wiki-hooks.py",
)


class WikiHookTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.projects_root = Path(self.temporary.name)
        self.project = self.projects_root / "api"
        self.project.mkdir()
        self.vault = self.projects_root / "platform wiki"
        wiki_setup.scaffold_vault(
            self.vault,
            "platform",
            "Explain how the platform projects fit together.",
            [self.project],
            ["**/.env"],
        )

    def tearDown(self):
        self.temporary.cleanup()

    def run_hook(self, name, payload):
        return subprocess.run(
            [sys.executable, str(self.vault / "hooks" / name)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )

    def initialize_clean_project(self):
        subprocess.run(["git", "init", "-q"], cwd=self.project, check=True)
        subprocess.run(["git", "add", ".wiki.json"], cwd=self.project, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Wiki Tests",
                "-c",
                "user.email=wiki-tests@example.invalid",
                "commit",
                "-qm",
                "initialize project",
            ],
            cwd=self.project,
            check=True,
        )

    def test_merge_preserves_unrelated_hooks_and_is_idempotent(self):
        existing = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "^Bash$",
                        "hooks": [{"type": "command", "command": "check-bash"}],
                    }
                ]
            }
        }

        merged = hook_installer.merge_hooks(existing, "codex", self.vault)

        self.assertEqual(merged["hooks"]["PreToolUse"], existing["hooks"]["PreToolUse"])
        self.assertEqual(len(merged["hooks"]["SessionStart"]), 1)
        self.assertEqual(len(merged["hooks"]["SessionEnd"]), 1)
        self.assertEqual(
            hook_installer.merge_hooks(merged, "codex", self.vault),
            merged,
        )

    def test_remove_deletes_only_this_vault_handlers(self):
        other_vault = self.projects_root / "other-wiki"
        existing = hook_installer.merge_hooks({}, "claude", other_vault)
        existing = hook_installer.merge_hooks(existing, "claude", self.vault)

        removed = hook_installer.merge_hooks(
            existing,
            "claude",
            self.vault,
            remove=True,
        )

        serialized = json.dumps(removed)
        self.assertNotIn(str(self.vault.resolve()), serialized)
        self.assertIn(str(other_vault.resolve()), serialized)

    def test_update_config_backs_up_changed_file(self):
        config = self.projects_root / "hooks.json"
        original = '{"hooks": {"PreToolUse": []}}\n'
        config.write_text(original)

        changed = hook_installer.update_config(config, "codex", self.vault)

        self.assertTrue(changed)
        backups = list(self.projects_root.glob("hooks.json.bak.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), original)
        self.assertIn("SessionStart", json.loads(config.read_text())["hooks"])

    def test_malformed_config_is_unchanged(self):
        config = self.projects_root / "hooks.json"
        original = "{not-json\n"
        config.write_text(original)

        with self.assertRaisesRegex(ValueError, "invalid JSON"):
            hook_installer.update_config(config, "codex", self.vault)

        self.assertEqual(config.read_text(), original)
        self.assertEqual(list(self.projects_root.glob("hooks.json.bak.*")), [])

    def test_session_start_emits_bounded_context_for_scoped_project(self):
        result = self.run_hook(
            "wiki-session-start.py",
            {
                "hook_event_name": "SessionStart",
                "cwd": str(self.project),
                "session_id": "session-1",
            },
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("platform Working Context", result.stdout)
        self.assertLessEqual(len(result.stdout.encode("utf-8")), 8192)

    def test_session_start_is_silent_outside_scope(self):
        outside = self.projects_root / "outside"
        outside.mkdir()

        result = self.run_hook(
            "wiki-session-start.py",
            {
                "hook_event_name": "SessionStart",
                "cwd": str(outside),
                "session_id": "session-1",
            },
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_session_end_queues_metadata_without_transcript_or_filenames(self):
        self.initialize_clean_project()
        (self.project / "changed-secret-name.txt").write_text("changed\n")

        result = self.run_hook(
            "wiki-session-end.py",
            {
                "hook_event_name": "SessionEnd",
                "cwd": str(self.project),
                "session_id": "session-1",
                "last_assistant_message": "private transcript text",
                "reason": "other",
            },
        )

        self.assertEqual(result.returncode, 0)
        queued = list((self.vault / "queues" / "review").glob("session-*.json"))
        self.assertEqual(len(queued), 1)
        candidate = json.loads(queued[0].read_text())
        self.assertEqual(candidate["cwd"], str(self.project.resolve()))
        self.assertEqual(candidate["session_id"], "session-1")
        self.assertEqual(candidate["dirty_file_count"], 1)
        serialized = json.dumps(candidate)
        self.assertNotIn("private transcript text", serialized)
        self.assertNotIn("changed-secret-name.txt", serialized)

    def test_session_end_does_not_queue_clean_project(self):
        self.initialize_clean_project()

        result = self.run_hook(
            "wiki-session-end.py",
            {
                "hook_event_name": "SessionEnd",
                "cwd": str(self.project),
                "session_id": "session-clean",
                "reason": "other",
            },
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            list((self.vault / "queues" / "review").glob("session-*.json")),
            [],
        )


if __name__ == "__main__":
    unittest.main()
