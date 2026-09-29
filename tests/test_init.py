"""Tests for scripts/init.sh CODEOWNERS handling, and this repo's own CODEOWNERS.

init.sh runs against throwaway git repos with stub `openspec` and `gh` binaries first on PATH,
so the tests need only python3 and PyYAML and never touch the network.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1]
INIT = TEMPLATE / "scripts/init.sh"
LIFECYCLE_PATHS = ["/AGENTS.md", "/CLAUDE.md", "/.claude/", "/.agents/", "/.github/", "/scripts/",
                   "/openspec/config.yaml", "/openspec/changes/", "/docs/decisions/"]

STUB_OPENSPEC = """#!/usr/bin/env bash
# Stub: `openspec init` creates the minimal layout init.sh expects.
if [[ "$1" == init ]]; then
  mkdir -p openspec/specs openspec/changes/archive
  printf 'schema: spec-driven\\n' > openspec/config.yaml
fi
"""
STUB_GH = "#!/usr/bin/env bash\nexit 1\n"  # behaves like an unauthenticated gh


class InitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.bin = root / "bin"
        self.bin.mkdir()
        for name, body in (("openspec", STUB_OPENSPEC), ("gh", STUB_GH)):
            (self.bin / name).write_text(body)
            (self.bin / name).chmod(0o755)
        self.target = root / "target"
        self.target.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        (self.target / "app.py").write_text("x = 1\n")
        self.commit()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.target, capture_output=True, text=True).stdout

    def commit(self) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "c")

    def init(self, *args: str) -> subprocess.CompletedProcess:
        env = {**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}"}
        return subprocess.run([str(INIT), *args], capture_output=True, text=True, env=env,
                              stdin=subprocess.DEVNULL)

    def codeowners(self) -> Path:
        return self.target / ".github/CODEOWNERS"

    def test_owner_renders(self):
        r = self.init("--owner", "@acme/maintainers", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        text = self.codeowners().read_text()
        for path in LIFECYCLE_PATHS:
            self.assertRegex(text, rf"(?m)^{path}\s+@acme/maintainers$")
        self.assertNotIn("@kwcantrell", text)
        self.assertNotIn("@OWNER", text)

    def test_no_owner_skips_with_warning(self):
        r = self.init(str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.codeowners().exists())
        next_steps = r.stdout.split("Next steps", 1)[1]
        first_item = next(line for line in next_steps.splitlines() if line.strip().startswith("1."))
        self.assertIn("CODEOWNERS", first_item)

    def test_invalid_owner_rejected_before_writes(self):
        for bad in ("acme", "@a#b", "@a\n/* @attacker", "@a&b", "@-bad", ""):
            with self.subTest(owner=bad):
                r = self.init("--owner", bad, str(self.target))
                self.assertNotEqual(r.returncode, 0, r.stdout)
                self.assertIn("owner", r.stderr.lower())
                self.assertEqual(self.git("status", "--porcelain"), "", "files were written")

    def test_valid_owner_forms_accepted(self):
        for good in ("@kalen", "@acme/platform-team", "dev@example.com"):
            with self.subTest(owner=good):
                r = self.init("--dry-run", "--owner", good, str(self.target))
                self.assertEqual(r.returncode, 0, r.stderr)

    def test_existing_codeowners_kept(self):
        for loc in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
            with self.subTest(location=loc):
                self.setUp()
                existing = self.target / loc
                existing.parent.mkdir(parents=True, exist_ok=True)
                existing.write_text("* @someone\n")
                self.commit()
                r = self.init("--owner", "@acme/maintainers", str(self.target))
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(existing.read_text(), "* @someone\n")
                if loc != ".github/CODEOWNERS":
                    self.assertFalse(self.codeowners().exists())
                self.assertIn(loc, r.stdout.split("skipped", 1)[1])
                self.assertIn("/openspec/changes/", r.stdout)  # paths to add by hand
                self.tearDown()

    def test_dry_run_reports_codeowners(self):
        cases = [(["--owner", "@acme/x"], "would render .github/CODEOWNERS for @acme/x"),
                 ([], "would skip CODEOWNERS: no owner")]
        for args, expected in cases:
            with self.subTest(args=args):
                r = self.init("--dry-run", *args, str(self.target))
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn(expected, r.stdout)
                self.assertEqual(self.git("status", "--porcelain"), "")
        (self.target / "CODEOWNERS").write_text("* @someone\n")
        self.commit()
        r = self.init("--dry-run", "--owner", "@acme/x", str(self.target))
        self.assertIn("would skip CODEOWNERS: CODEOWNERS exists", r.stdout)

    def test_owner_flag_missing_value(self):
        r = self.init(str(self.target), "--owner")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--owner needs a value", r.stderr)
        r = self.init("--owner", "--dry-run", str(self.target))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--owner needs a value", r.stderr)


class RepoCodeownersTest(unittest.TestCase):
    def test_repo_codeowners_names_owner(self):
        text = (TEMPLATE / ".github/CODEOWNERS").read_text()
        self.assertNotIn("@OWNER", text)
        for path in LIFECYCLE_PATHS:
            self.assertRegex(text, rf"(?m)^{path}\s+@kwcantrell$")

    def test_template_covers_the_same_paths(self):
        text = (TEMPLATE / "scripts/templates/CODEOWNERS.tmpl").read_text()
        for path in LIFECYCLE_PATHS:
            self.assertRegex(text, rf"(?m)^{path}\s+@OWNER$")


if __name__ == "__main__":
    unittest.main()
