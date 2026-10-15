"""Check shared state identity, preservation, and local Git exclusions in temporary repositories."""

from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run import build, render, snapshot, write_vars


class SharedState(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.config = self.folder / "config"
        self.repo = build(self.folder / "project_name", {})
        self.vars = write_vars(self.folder, {})

    def run_setup(self, repo=None, args=None):
        result = render(repo or self.repo, args or ["--vars", "{vars}"], self.vars, self.config)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def state(self, repo=None):
        return self.config / "killall-skills/agents/state" / re.sub(r"[^A-Za-z0-9]", "-", str(repo or self.repo))

    def test_shared_across_hosts_and_worktrees(self):
        from make_repo import git

        self.run_setup(args=["--vars", "{vars}", "--hosts", "claude"])
        linked = self.folder / "linked"
        git(self.repo, "worktree", "add", "-q", "-b", "lane/test", str(linked))
        self.run_setup(linked, ["--vars", "{vars}", "--hosts", "codex"])
        state = self.state()
        self.assertTrue((state / "README.md").is_file())
        self.assertEqual(list(state.parent.iterdir()), [state])
        for path in (self.repo / ".claude/agents/orchestrator.md", linked / ".codex/config.toml"):
            self.assertIn(str(state), path.read_text(encoding="utf-8"))
        self.assertEqual(state.stat().st_mode & 0o777, 0o700)

    def test_rerun_and_remove_keep_lane_records(self):
        self.run_setup()
        state = self.state()
        lane = state / "auth.json"
        content = json.dumps({"task": "Validate login", "status": "working", "worktree": str(self.repo)})
        lane.write_text(content, encoding="utf-8")
        self.run_setup()
        self.run_setup(args=["--remove"])
        self.assertEqual(lane.read_text(encoding="utf-8"), content)
        self.assertTrue((state / "README.md").is_file())

    def test_encoding_collision_refused_even_with_force(self):
        self.run_setup()
        other = build(self.folder / "project-name", {})
        before = snapshot(other)
        for args in (["--vars", "{vars}"], ["--vars", "{vars}", "--force"]):
            result = render(other, args, self.vars, self.config)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("another repository", result.stderr)
            self.assertEqual(snapshot(other), before)

    def test_only_generated_agents_are_ignored_and_subset_rerun_keeps_ignores(self):
        from make_repo import git

        self.run_setup()
        self.run_setup(args=["--vars", "{vars}", "--hosts", "codex"])
        for path in (".claude/agents/builder.md", ".codex/agents/reviewer.toml", ".cursor/rules/orchestrator.mdc", ".claude/settings.json", ".codex/config.toml"):
            self.assertEqual(git(self.repo, "check-ignore", path), path)
        self.assertNotIn("custom.md", (self.repo / ".git/info/exclude").read_text(encoding="utf-8"))
        self.run_setup(args=["--remove"])
        self.assertNotIn("agent-setup:start", (self.repo / ".git/info/exclude").read_text(encoding="utf-8"))

    def test_foreign_project_setting_leaves_state_untouched(self):
        config = self.repo / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text('model = "local"\n', encoding="utf-8")
        result = render(self.repo, ["--vars", "{vars}"], self.vars, self.config)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.state().exists())

    def test_default_is_under_home_config(self):
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        from render_agents import project_state

        for value in (None, "", "relative/config"):
            with self.subTest(config_home=value), patch.dict(os.environ):
                if value is None:
                    os.environ.pop("XDG_CONFIG_HOME", None)
                else:
                    os.environ["XDG_CONFIG_HOME"] = value
                root, state = project_state(self.repo)
                self.assertEqual(root, self.repo)
                self.assertEqual(state.parent, Path.home() / ".config/killall-skills/agents/state")


if __name__ == "__main__":
    unittest.main()
