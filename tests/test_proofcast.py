import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PROOFCAST = REPO / "scripts" / "proofcast"
SKILL = REPO / "plugins" / "experimental" / "skills" / "record" / "SKILL.md"


class ProofcastTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self._tool(
            "asciinema",
            """#!/usr/bin/env bash
set -u
if [ "${1:-}" = convert ]; then
  cat "$4"
  exit 0
fi
command=
cast=
while [ "$#" -gt 0 ]; do
  case "$1" in
    --command) command=$2; shift 2 ;;
    --*) shift ;;
    record) shift ;;
    *) cast=$1; shift ;;
  esac
done
/bin/bash -c "$command" >"$cast" 2>&1
exit $?
""",
        )
        self._tool(
            "agg",
            """#!/usr/bin/env bash
cp "$1" "$2"
""",
        )
        self._tool(
            "ffmpeg",
            """#!/usr/bin/env bash
for arg in "$@"; do output=$arg; done
printf mp4 >"$output"
""",
        )
        self.env = os.environ.copy()
        self.env["PATH"] = f"{self.bin}:{self.env['PATH']}"

    def tearDown(self):
        self.temp.cleanup()

    def _tool(self, name, body):
        path = self.bin / name
        path.write_text(body)
        path.chmod(0o755)

    def run_proofcast(self, *args):
        return subprocess.run(
            [str(PROOFCAST), *args],
            cwd=self.root,
            env=self.env,
            text=True,
            capture_output=True,
        )

    def test_records_command_to_one_default_mp4(self):
        result = self.run_proofcast("--", "python3", "-c", "print('proofcast ok')")

        self.assertEqual(result.returncode, 0, result.stderr)
        outputs = list(self.root.glob("proofcast-*.mp4"))
        self.assertEqual(len(outputs), 1)
        self.assertIn("proofcast ok", result.stdout)
        self.assertTrue(Path(result.stdout.splitlines()[-1]).samefile(outputs[0]))

    def test_out_selects_exact_path_and_refuses_overwrite(self):
        output = self.root / "review.mp4"
        first = self.run_proofcast("--out", str(output), "--", "printf", "hello")
        second = self.run_proofcast("--out", str(output), "--", "printf", "again")

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout.splitlines()[-1], str(output))
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("already exists", second.stderr)

    def test_failed_command_still_produces_video_and_returns_command_status(self):
        output = self.root / "failure.mp4"
        result = self.run_proofcast(
            "--out", str(output), "--", "python3", "-c", "print('failed'); raise SystemExit(7)"
        )

        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertTrue(output.is_file())
        self.assertIn("failed", result.stdout)
        self.assertEqual(result.stdout.splitlines()[-1], str(output))

    def test_requires_a_command(self):
        result = self.run_proofcast()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("usage:", result.stderr.lower())

    def test_task_install_links_the_script(self):
        home = self.root / "home"
        env = self.env | {"HOME": str(home)}

        first = subprocess.run(
            ["task", "install"], cwd=REPO, env=env, text=True, capture_output=True
        )
        second = subprocess.run(
            ["task", "install"], cwd=REPO, env=env, text=True, capture_output=True
        )

        link = home / ".local" / "bin" / "proofcast"
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), PROOFCAST.resolve())

    def test_record_skill_requires_explicit_safe_recording_and_mp4_link(self):
        skill = SKILL.read_text()

        self.assertIn("only when the user explicitly asks", skill)
        self.assertIn("Never include or print passwords", skill)
        self.assertIn("proofcast [--out <video.mp4>] -- <command>", skill)
        self.assertIn("I stopped the recording.", skill)
        self.assertIn("clickable link to the MP4", skill)


if __name__ == "__main__":
    unittest.main()
