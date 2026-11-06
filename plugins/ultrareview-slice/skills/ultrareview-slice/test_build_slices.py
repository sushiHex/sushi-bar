"""Offline checks for the billing guards. Run: python -I -B test_build_slices.py (no billed calls)."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_slices as bs  # noqa: E402


def fake_claude(folder: Path, status: dict) -> str:
    """A `claude auth status` stand-in: a script that prints the given JSON."""
    script = folder / "fake_claude.py"
    script.write_text(f"import sys\nprint({json.dumps(json.dumps(status))})\n", encoding="utf-8")
    if os.name == "nt":
        shim = folder / "fake_claude.cmd"
        shim.write_text(f'@"{sys.executable}" "{script}" %*\n', encoding="ascii")
        return str(shim)
    shim = folder / "fake_claude"
    shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="ascii")
    shim.chmod(0o755)
    return str(shim)


class FindingLimit(unittest.TestCase):
    def test_accepts_all_and_positive_counts(self):
        self.assertEqual(bs.finding_limit("all"), "all")
        self.assertEqual(bs.finding_limit("7"), "7")

    def test_rejects_everything_else(self):
        for bad in ("0", "-3", "", "ALL", "1.5", "٣"):
            with self.assertRaises(argparse.ArgumentTypeError, msg=bad):
                bs.finding_limit(bad)


class CloudAuth(unittest.TestCase):
    def check(self, status):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            exe = fake_claude(folder, status)
            bs.verify_cloud_auth(exe, folder, dict(os.environ))

    def test_subscription_login_passes(self):
        self.check({"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty"})

    def test_api_key_and_third_party_are_refused(self):
        for status in ({"loggedIn": True, "authMethod": "api_key"},
                       {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "bedrock"},
                       {"loggedIn": False, "authMethod": "claude.ai"}):
            with self.assertRaises(SystemExit, msg=str(status)):
                self.check(status)

    def test_missing_executable_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                bs.verify_cloud_auth(str(Path(tmp) / "nope"), Path(tmp), dict(os.environ))


class LaunchBilling(unittest.TestCase):
    """`claude` on PATH is a recording stub, so a regressed guard can never bill."""

    def run_launch(self, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, bindir, record = root / "repo", root / "bin", root / "calls.txt"
            bindir.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / ".git" / "ultra-slices.json").write_text(
                json.dumps({"build": "t", "base_ref": "x", "commit": "0" * 40, "slices": [
                    {"n": 1, "worktree": str(repo), "branch": "b", "base": "0" * 40,
                     "head": "0" * 40, "files": [], "lines": 0}]}), encoding="utf-8")
            stub = bindir / "claude_stub.py"
            stub.write_text(f"import sys\nopen({str(record)!r}, 'a').write(' '.join(sys.argv[1:]) + '\\n')\n"
                            "print('{}')\n", encoding="utf-8")
            if os.name == "nt":
                (bindir / "claude.cmd").write_text(f'@"{sys.executable}" "{stub}" %*\n', encoding="ascii")
            else:
                shim = bindir / "claude"
                shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{stub}" "$@"\n', encoding="ascii")
                shim.chmod(0o755)
            env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ.get("PATH", ""))
            result = subprocess.run([sys.executable, "-I", "-B", str(HERE / "build_slices.py"),
                                     "launch", "--repo", str(repo), "--trust-workspace", *extra],
                                    capture_output=True, text=True, encoding="utf-8", env=env)
            calls = record.read_text(encoding="utf-8").splitlines() if record.exists() else []
            return result, calls

    def test_launch_without_the_acknowledgement_never_reaches_claude(self):
        result, calls = self.run_launch()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--billing usage-credits", result.stderr + result.stdout)
        self.assertEqual(calls, [])

    def test_launch_with_the_acknowledgement_reaches_claude(self):
        result, calls = self.run_launch("--billing", "usage-credits")
        self.assertEqual(len(calls), 1, result.stderr + result.stdout)
        self.assertTrue(calls[0].startswith("ultrareview "), calls)


if __name__ == "__main__":
    unittest.main()
