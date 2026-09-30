"""Tests for scripts/init.sh CODEOWNERS handling, and this repo's own CODEOWNERS.

init.sh runs against throwaway git repos with stub `openspec` and `gh` binaries first on PATH,
so the tests need only python3 and PyYAML and never touch the network.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
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
  mkdir -p openspec/specs openspec/changes/archive .claude/skills/openspec-propose
  [[ -e openspec/config.yaml ]] || printf 'schema: spec-driven\\n' > openspec/config.yaml
  [[ -e .claude/skills/openspec-propose/SKILL.md ]] || echo generated > .claude/skills/openspec-propose/SKILL.md
fi
"""
STUB_GH = "#!/usr/bin/env bash\nexit 1\n"  # behaves like an unauthenticated gh


class InitFixture(unittest.TestCase):
    """A throwaway target repo with stub `openspec` and `gh` first on PATH."""

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


class InitTest(InitFixture):
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

    # Exact files init.sh installs and must list in the target's lifecycle.managed_paths.
    MANAGED = ["scripts/check-change.sh", "scripts/sync-skills.sh", "scripts/lib/check_change.py",
               "scripts/lib/adopt.py", ".claude/hooks/guard-approval.sh", ".claude/hooks/stop-check.sh"]

    def lifecycle(self, root: Path) -> dict:
        import yaml
        return yaml.safe_load((root / "openspec/config.yaml").read_text())["lifecycle"]

    def test_init_sets_managed_paths(self):
        r = self.init("--owner", "@acme/x", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.lifecycle(self.target)["managed_paths"], self.MANAGED)
        self.assertEqual(self.lifecycle(TEMPLATE)["managed_paths"], [])
        for path in self.MANAGED:
            self.assertTrue((self.target / path).is_file(), path)

    def test_init_keeps_existing_managed_paths(self):
        (self.target / "openspec").mkdir()
        (self.target / "openspec/config.yaml").write_text(
            "schema: spec-driven\nlifecycle:\n  managed_paths: [vendor/x.sh]\n")
        self.commit()
        r = self.init("--owner", "@acme/x", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.lifecycle(self.target)["managed_paths"], ["vendor/x.sh"])


class AdoptionTest(InitFixture):
    """Adopting into a repo that already has its own agent guidance: create-only, plus proposals."""

    def existing_setup(self) -> dict[str, bytes]:
        files = {
            "AGENTS.md": "# Mine\nUse a worktree.\n",
            "CLAUDE.md": "@AGENTS.md\n",
            ".claude/settings.json": json.dumps({"permissions": {"allow": ["Bash"]},
                                                 "enabledPlugins": {"p": True}}),
            "openspec/config.yaml": "schema: spec-driven\nrules:\n  proposal: [x]\n",
            ".agents/skills/mine/SKILL.md": "mine\n",
            ".claude/skills/openspec-propose/SKILL.md": "theirs\n",
        }
        for rel, text in files.items():
            (self.target / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.target / rel).write_text(text)
        (self.target / ".gitignore").write_text(".claude/settings.json\n")
        self.commit()
        return {rel: (self.target / rel).read_bytes() for rel in files}

    def status(self) -> str:
        return self.git("status", "--porcelain", "--ignored")

    def adopt_py(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(TEMPLATE / "scripts/lib/adopt.py"), *args],
                              capture_output=True, text=True)

    def test_existing_and_ignored_files_untouched(self):
        before = self.existing_setup()
        r = self.init("--owner", "@acme/x", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        for rel, data in before.items():
            self.assertEqual((self.target / rel).read_bytes(), data, rel)
        folder = self.target / ".lifecycle-adoption"
        for name in ("README.md", "settings.json", "openspec-config.snippet.yaml",
                     "AGENTS.block.md", "CLAUDE.block.md"):
            self.assertTrue((folder / name).is_file(), name)
        self.assertTrue((self.target / "docs/agent-lifecycle.md").is_file())
        self.assertTrue((self.target / ".agents/skills/risk-tier/SKILL.md").is_file())
        self.assertIn("Bash", r.stdout.split("Risks", 1)[1])

    def test_unwired_hooks_first_next_step(self):
        self.existing_setup()
        r = self.init("--owner", "@acme/x", str(self.target))
        next_steps = r.stdout.split("Next steps", 1)[1]
        first = next(line for line in next_steps.splitlines() if line.strip().startswith("1."))
        self.assertIn("hooks", first)
        self.assertIn("not active", first)

    def test_openspec_init_skipped_when_generated_files_exist(self):
        self.existing_setup()
        marker = self.target / "openspec-init-ran"
        (self.bin / "openspec").write_text(f"#!/usr/bin/env bash\ntouch {marker}\n")
        r = self.init("--owner", "@acme/x", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(marker.exists())
        self.assertIn("openspec init", r.stdout)

    def test_symlink_outside_repo_skipped(self):
        outside = Path(self.tmp.name) / "target-evil"  # shares the target's path prefix
        outside.mkdir()
        (self.target / "docs").symlink_to(outside, target_is_directory=True)
        self.commit()
        r = self.init("--owner", "@acme/x", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertIn("outside", r.stdout)

    def test_existing_adoption_folder_refused(self):
        (self.target / ".lifecycle-adoption").mkdir()
        (self.target / ".lifecycle-adoption/.gitignore").write_text("*\n")
        r = self.init("--owner", "@acme/x", str(self.target))
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.target / "AGENTS.md").exists())

    def test_adoption_folder_ignored(self):
        self.existing_setup()
        self.init("--owner", "@acme/x", str(self.target))
        self.assertNotIn(".lifecycle-adoption", self.git("status", "--porcelain"))

    def test_undo_restores_tree(self):
        before = self.status()
        r = self.init("--owner", "@acme/x", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotEqual(self.status(), before)
        u = self.adopt_py("undo", "--target", str(self.target))
        self.assertEqual(u.returncode, 0, u.stderr)
        self.assertEqual(self.status(), before)
        leftovers = [p for p in self.target.rglob("*") if ".git" not in p.parts and p.name != "app.py"]
        self.assertEqual(leftovers, [])

    def test_fresh_install_writes_config(self):
        r = self.init("--owner", "@acme/x", "--test", "make test", str(self.target))
        self.assertEqual(r.returncode, 0, r.stderr)
        import yaml
        lc = yaml.safe_load((self.target / "openspec/config.yaml").read_text())["lifecycle"]
        self.assertEqual(lc["commands"]["test"], "make test")
        self.assertIn("scripts/lib/adopt.py", lc["managed_paths"])
        folder = sorted(p.name for p in (self.target / ".lifecycle-adoption").iterdir())
        self.assertEqual(folder, [".gitignore", "MANIFEST", "README.md"])


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
