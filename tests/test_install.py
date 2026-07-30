import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
INSTALLER = REPO / "install.sh"


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

    def test_installs_both_plugin_hosts(self) -> None:
        result = self.run_installer()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("plugin marketplace add", result.install_log)
        self.assertIn("plugin install killall-skills@killallgit", result.install_log)
        self.assertIn("plugin add killall-skills@killallgit", result.install_log)

    def test_remove_uninstalls_from_both_hosts(self) -> None:
        result = self.run_installer("--remove")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("plugin uninstall killall-skills@killallgit", result.install_log)
        self.assertIn("plugin remove killall-skills@killallgit", result.install_log)
        self.assertNotIn("marketplace add", result.install_log)

    def test_rejects_unknown_argument(self) -> None:
        result = self.run_installer("--wat")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown argument", result.stderr)


if __name__ == "__main__":
    unittest.main()
