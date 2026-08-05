import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
INSTALLER = REPO / "install.sh"
DOMAINS = ("planning", "engineering", "architecture", "knowledge", "experimental")


class InstallerTests(unittest.TestCase):
    def make_host(self, directory: Path, name: str) -> None:
        host = directory / name
        host.write_text(
            "#!/bin/sh\n"
            'printf "%s %s\\n" "$0" "$*" >> "$INSTALL_LOG"\n'
        )
        host.chmod(0o755)

    def run_installer(self, *args: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_host(root, "claude")
            self.make_host(root, "codex")
            log = root / "install.log"
            environment = os.environ.copy()
            environment["PATH"] = f"{root}:{environment['PATH']}"
            environment["INSTALL_LOG"] = str(log)
            result = subprocess.run(
                [str(INSTALLER), *args],
                cwd=REPO,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            result.install_log = log.read_text() if log.exists() else ""
            return result

    def test_requires_a_domain_or_all(self) -> None:
        result = self.run_installer()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stdout)
        self.assertEqual(result.install_log, "")

    def test_lists_domains_without_calling_hosts(self) -> None:
        result = self.run_installer("--list")

        self.assertEqual(result.returncode, 0, result.stderr)
        for domain in DOMAINS:
            self.assertIn(domain, result.stdout)
        self.assertEqual(result.install_log, "")

    def test_installs_one_domain_in_both_plugin_hosts(self) -> None:
        result = self.run_installer("planning")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("plugin marketplace add", result.install_log)
        codex_calls = [
            line.split(" ", 1)[1]
            for line in result.install_log.splitlines()
            if Path(line.split(" ", 1)[0]).name == "codex"
        ]
        self.assertLess(
            codex_calls.index("plugin marketplace remove killallgit"),
            next(
                index
                for index, call in enumerate(codex_calls)
                if call.startswith("plugin marketplace add ")
            ),
        )
        self.assertIn("plugin install planning@killallgit", result.install_log)
        self.assertIn("plugin add planning@killallgit", result.install_log)
        self.assertNotIn("engineering@killallgit", result.install_log)

    def test_installs_multiple_selected_domains(self) -> None:
        result = self.run_installer("planning", "engineering")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("plugin install planning@killallgit", result.install_log)
        self.assertIn("plugin install engineering@killallgit", result.install_log)
        self.assertNotIn("architecture@killallgit", result.install_log)

    def test_all_installs_every_domain(self) -> None:
        result = self.run_installer("--all")

        self.assertEqual(result.returncode, 0, result.stderr)
        for domain in DOMAINS:
            self.assertIn(f"plugin install {domain}@killallgit", result.install_log)
            self.assertIn(f"plugin add {domain}@killallgit", result.install_log)

    def test_remove_uninstalls_only_selected_domain(self) -> None:
        result = self.run_installer("--remove", "knowledge")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("plugin uninstall knowledge@killallgit", result.install_log)
        self.assertIn("plugin remove knowledge@killallgit", result.install_log)
        self.assertNotIn("marketplace add", result.install_log)
        self.assertNotIn("planning@killallgit", result.install_log)

    def test_rejects_unknown_argument(self) -> None:
        result = self.run_installer("--wat")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown argument", result.stderr)
        self.assertEqual(result.install_log, "")

    def test_rejects_unknown_domain_before_calling_hosts(self) -> None:
        result = self.run_installer("planning", "nope")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown domain", result.stderr)
        self.assertEqual(result.install_log, "")


if __name__ == "__main__":
    unittest.main()
