"""Tests for scripts/lib/check_change.py and the Claude Code hooks.

Each test builds a throwaway git repo with the template's scripts and config, makes a branch
that represents a PR, and runs the checker against it.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEMPLATE / "scripts/lib"))


def sh(cwd: Path, *args: str, env: dict | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, input=stdin,
                          env={**os.environ, **(env or {})})


class Repo:
    def __init__(self, lifecycle: dict | None = None) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        for rel in ("scripts", "openspec/config.yaml", "AGENTS.md", ".claude/hooks"):
            src, dst = TEMPLATE / rel, self.path / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst) if src.is_dir() else shutil.copy(src, dst)
        # Like init.sh: the template's own commands and source globs are not carried over.
        cfg = self.path / "openspec/config.yaml"
        text = re.sub(r'^(    (?:test|lint|typecheck|audit|build)): ".*?"', r'\1: ""', cfg.read_text(), flags=re.M)
        cfg.write_text(re.sub(r"^  source_globs: .*$", "  source_globs: []", text, flags=re.M))
        if lifecycle:  # base-branch lifecycle settings for this test
            import yaml
            data = yaml.safe_load(cfg.read_text())
            data["lifecycle"].update(lifecycle)
            cfg.write_text(yaml.safe_dump(data, sort_keys=False))
        (self.path / "openspec/changes/archive").mkdir(parents=True)
        (self.path / "openspec/specs").mkdir(parents=True)
        (self.path / "src").mkdir()
        (self.path / "src/app.py").write_text("x = 1\n")
        for cmd in (["git", "init", "-q", "-b", "main"], ["git", "config", "user.email", "t@example.com"],
                    ["git", "config", "user.name", "t"], ["git", "config", "commit.gpgsign", "false"]):
            sh(self.path, *cmd)
        self.commit("base")
        sh(self.path, "git", "checkout", "-q", "-b", "feature")

    def write(self, rel: str, text: str) -> None:
        p = self.path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(text))

    def commit(self, msg: str) -> None:
        sh(self.path, "git", "add", "-A")
        sh(self.path, "git", "commit", "-q", "-m", msg)

    def change(self, tier: int, approved: bool = True, tasks: str = "- [x] 1.1 Do it\n  Evidence: `pytest` -> 3 passed\n",
               panel: str | None = None) -> None:
        d = "openspec/changes/add-thing"
        approval = "Approved-by: Alice 2026-09-29\n" if approved else ""
        self.write(f"{d}/proposal.md", f"# Add thing\n\nTier: {tier}\n{approval}\n## Why\n\nBecause.\n")
        self.write(f"{d}/tasks.md", "## 1. Build\n\n" + tasks)
        if panel is not None:
            self.write(f"{d}/panel.md", panel)

    def check(self, *only: str, env: dict | None = None) -> tuple[int, str]:
        # Clear CI context so a real PR's event (its Tier, labels, base) can't leak into the test.
        ci = {"CI": "", "GITHUB_EVENT_PATH": "", "GITHUB_BASE_REF": ""}
        r = sh(self.path, "scripts/check-change.sh", "--only", ",".join(only), env={**ci, **(env or {})})
        return r.returncode, r.stdout + r.stderr

    def close(self) -> None:
        self.tmp.cleanup()


class CheckerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Repo()

    def tearDown(self) -> None:
        self.repo.close()

    def assertStatus(self, only: str, status: str, env: dict | None = None) -> str:
        rc, out = self.repo.check(only, env=env)
        self.assertIn(f"{status:<4}  {only}", out, out)
        self.assertEqual(rc, 1 if status == "FAIL" else 0, out)
        return out

    def test_tier0_docs_change_passes(self):
        self.repo.write("docs/readme.md", "hello\n")
        self.repo.commit("docs")
        self.assertStatus("change", "PASS")
        self.assertStatus("approval", "SKIP")

    def test_missing_tier_line_fails(self):
        self.repo.write("openspec/changes/x/proposal.md", "# X\n\n## Why\n")
        self.assertStatus("change", "FAIL")

    def test_two_changes_on_one_branch_fail(self):
        self.repo.change(1)
        self.repo.write("openspec/changes/other/proposal.md", "# O\n\nTier: 1\n")
        self.assertStatus("change", "FAIL")

    def test_tier1_needs_approval(self):
        self.repo.change(1, approved=False)
        self.assertStatus("approval", "FAIL")
        self.repo.change(1, approved=True)
        self.assertStatus("approval", "PASS")

    def test_pr_body_tier_must_match_proposal(self):
        self.repo.change(1)
        event = self.repo.path / "event.json"
        event.write_text(json.dumps({"pull_request": {"body": "Tier: 2\n", "labels": []}}))
        out = self.assertStatus("change", "FAIL", env={"GITHUB_EVENT_PATH": str(event)})
        self.assertIn("PR says tier 2", out)

    def test_ticked_task_without_evidence_fails(self):
        self.repo.change(1, tasks="- [x] 1.1 Do it\n- [x] 1.2 Other\n  Evidence: ran it\n")
        out = self.assertStatus("evidence", "FAIL")
        self.assertIn("1.1 Do it", out)

    def test_unticked_task_fails_tasks_gate(self):
        self.repo.change(1, tasks="- [ ] 1.1 Not yet\n")
        self.assertStatus("tasks", "FAIL")

    def test_tier2_needs_panel_without_open_criticals(self):
        self.repo.change(2)
        self.assertStatus("panel", "FAIL")
        self.repo.change(2, panel="- [ ] [critical] Drops rows\n- [x] [major] Fixed\n")
        self.assertStatus("panel", "FAIL")
        self.repo.change(2, panel="- [x] [critical] Drops rows. Resolved: fixed\n- [ ] [minor] Rename\n")
        self.assertStatus("panel", "PASS")

    def test_high_risk_path_forces_tier2(self):
        self.repo.change(1)
        self.repo.write("scripts/extra.sh", "echo\n")
        self.assertStatus("risk-floor", "FAIL")
        self.repo.change(2)
        self.assertStatus("risk-floor", "PASS")

    def test_artifacts_first_commit(self):
        self.repo.change(1)
        self.repo.write("src/app.py", "x = 2\n")
        self.repo.commit("artifacts and code together")
        self.assertStatus("artifacts-first", "FAIL")

    def test_artifacts_first_commit_passes_when_plan_pinned(self):
        self.repo.change(1)
        self.repo.commit("artifacts")
        self.repo.write("src/app.py", "x = 2\n")
        self.repo.commit("code")
        self.assertStatus("artifacts-first", "PASS")

    def test_source_without_tests_fails_and_label_overrides(self):
        cfg = self.repo.path / "openspec/config.yaml"
        cfg.write_text(cfg.read_text().replace("source_globs: []", 'source_globs: ["src/**"]'))
        self.repo.commit("config")
        self.repo.write("src/app.py", "x = 3\n")
        self.assertStatus("tests-with-code", "FAIL")
        event = self.repo.path / "event.json"
        event.write_text(json.dumps({"pull_request": {"body": "", "labels": [{"name": "no-test-needed"}]}}))
        self.assertStatus("tests-with-code", "WARN", env={"GITHUB_EVENT_PATH": str(event)})
        self.repo.write("tests/test_app.py", "def test(): pass\n")
        self.assertStatus("tests-with-code", "PASS")

    def test_size_budget(self):
        self.repo.write("src/big.py", "".join(f"v{i} = {i}\n" for i in range(401)))
        self.repo.commit("big")
        self.assertStatus("size", "FAIL")
        self.assertStatus("size", "WARN", env={"LIFECYCLE_OVERRIDE": "size_budget: generated code"})

    def test_size_budget_ignores_tests_and_lockfiles(self):
        self.repo.write("tests/test_big.py", "".join(f"v{i} = {i}\n" for i in range(500)))
        self.repo.write("uv.lock", "x\n" * 500)
        self.repo.commit("big but excluded")
        self.assertStatus("size", "PASS")

    def test_unpinned_action_fails(self):
        self.repo.write(".github/workflows/ci.yml", """\
            name: ci
            on: push
            permissions:
              contents: read
            jobs:
              a:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@v4
            """)
        self.assertStatus("workflows", "FAIL")

    def test_pinned_action_with_permissions_passes(self):
        self.repo.write(".github/workflows/ci.yml", """\
            name: ci
            on: push
            permissions:
              contents: read
            jobs:
              a:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
                  - uses: ./local-action
            """)
        self.assertStatus("workflows", "PASS")

    def test_skills_out_of_sync_fails(self):
        self.repo.write(".claude/skills/demo/SKILL.md", "---\nname: demo\n---\n")
        self.assertStatus("skills-sync", "FAIL")
        sh(self.repo.path, "scripts/sync-skills.sh")
        self.assertStatus("skills-sync", "PASS")

    def test_guide_size(self):
        self.repo.write("AGENTS.md", "line\n" * 151)
        self.assertStatus("guide-size", "FAIL")

    def test_failing_command_fails(self):
        cfg = self.repo.path / "openspec/config.yaml"
        cfg.write_text(cfg.read_text().replace('test: ""', 'test: "exit 3"', 1))
        out = self.assertStatus("commands", "FAIL")
        self.assertIn("exited 3", out)


class PanelFormatTest(unittest.TestCase):
    """The panel gate enforces the checklist format instead of assuming it."""

    def setUp(self) -> None:
        self.repo = Repo()

    def tearDown(self) -> None:
        self.repo.close()

    def panel(self, text: str) -> tuple[int, str]:
        self.repo.change(2, panel=textwrap.dedent(text))
        return self.repo.check("panel")

    def assertPanel(self, text: str, status: str, needle: str = "") -> None:
        rc, out = self.panel(text)
        self.assertIn(f"{status:<4}  panel", out, out)
        self.assertIn(needle, out)

    def test_prose_panel_fails(self):
        self.assertPanel("# Panel\n\nThree critical issues were found and fixed.\n",
                         "FAIL", "no findings in checklist format")

    def test_no_findings_panel_passes(self):
        self.assertPanel("# Panel\n\nNo findings.  \n", "PASS")

    def test_no_findings_in_code_block_fails(self):
        self.assertPanel("# Panel\n\n```\nNo findings.\n```\n<!--\nNo findings.\n-->\n",
                         "FAIL", "no findings in checklist format")

    def test_untagged_panel_item_fails(self):
        for item in ("- [ ] Drops rows", "- [ ] [Critical] Drops rows", "- [x] fixed [minor] thing"):
            with self.subTest(item=item):
                self.assertPanel(f"- [x] [minor] ok. Resolved: yes\n{item}\n", "FAIL", "untagged")

    def test_nested_sub_bullet_not_a_finding(self):
        self.assertPanel("- [x] [major] Retry unbounded. Resolved: capped at 3\n  - [ ] see above\n", "PASS")

    def test_ticked_critical_needs_resolution(self):
        self.assertPanel("- [x] [critical] Drops rows\n", "FAIL", "without Resolved:")
        self.assertPanel("- [x] [critical] Drops rows. Declined by human: out of scope\n", "PASS")
        self.assertPanel("- [x] [minor] Rename\n", "PASS")

    def test_open_critical_still_fails(self):
        self.assertPanel("- [ ] [critical] Drops rows\n", "FAIL", "open critical")


class ExemptionTest(unittest.TestCase):
    """Test-folder globs, managed paths, and exemptions read from the base branch."""

    def tearDown(self) -> None:
        self.repo.close()

    def test_nested_tests_dir_counts_as_tests(self):
        self.repo = Repo(lifecycle={"source_globs": ["src/**"]})
        self.repo.write("src/app.sh", "echo 2\n")
        self.repo.write("scripts/tests/test-app.sh", "echo ok\n")
        rc, out = self.repo.check("tests-with-code")
        self.assertIn("PASS  tests-with-code", out, out)

    def test_managed_paths_ignored_by_tests_with_code(self):
        self.repo = Repo(lifecycle={"source_globs": ["vendor/**"], "managed_paths": ["vendor/tool.sh"]})
        self.repo.write("vendor/tool.sh", "#!/bin/sh\necho updated\n")
        rc, out = self.repo.check("tests-with-code")
        self.assertIn("PASS  tests-with-code", out, out)

    def test_managed_paths_ignored_by_size(self):
        self.repo = Repo(lifecycle={"managed_paths": ["vendor/tool.py"]})
        self.repo.write("vendor/tool.py", "".join(f"v{i} = {i}\n" for i in range(600)))
        self.repo.commit("vendored update")
        rc, out = self.repo.check("size")
        self.assertIn("PASS  size", out, out)

    def test_pr_cannot_grant_own_exemption(self):
        self.repo = Repo(lifecycle={"source_globs": ["src/**"]})
        cfg = self.repo.path / "openspec/config.yaml"
        cfg.write_text(cfg.read_text().replace("lifecycle:\n", "lifecycle:\n  managed_paths: ['src/**']\n", 1))
        self.repo.write("src/app.py", "x = 9\n")
        self.repo.commit("exempt my own source")
        rc, out = self.repo.check("tests-with-code")
        self.assertIn("FAIL  tests-with-code", out, out)


class OnlyTest(unittest.TestCase):
    """--only must not change results, hide a change failure, or crash on bad input."""

    def setUp(self) -> None:
        self.repo = Repo()

    def tearDown(self) -> None:
        self.repo.close()

    def run_only(self, only: str, env: dict | None = None) -> tuple[int, list[str], str]:
        ci = {"CI": "", "GITHUB_EVENT_PATH": "", "GITHUB_BASE_REF": ""}
        r = sh(self.repo.path, "scripts/check-change.sh", "--only", only, env={**ci, **(env or {})})
        lines = [line.split()[0] + " " + line.split()[1] for line in r.stdout.splitlines() if line.strip()]
        return r.returncode, lines, r.stdout + r.stderr

    def approved_tier2(self) -> None:
        self.repo.change(2, panel="- [x] [critical] Fixed. Resolved: yes\n")

    def test_only_order_does_not_change_results(self):
        self.approved_tier2()
        for only in ("approval,panel,change", "change,approval,panel"):
            with self.subTest(only=only):
                rc, lines, out = self.run_only(only)
                self.assertEqual(lines, [f"PASS {n}" for n in only.split(",")], out)
                self.assertEqual(rc, 0, out)

    def test_only_without_change_still_resolves_it(self):
        self.approved_tier2()
        rc, lines, out = self.run_only("approval,panel")
        self.assertEqual(lines, ["PASS approval", "PASS panel"], out)

    def test_change_failure_not_swallowed(self):
        self.repo.change(1)
        self.repo.write("openspec/changes/other/proposal.md", "# O\n\nTier: 1\n")
        rc, lines, out = self.run_only("approval")
        self.assertEqual(lines, ["FAIL change", "SKIP approval"], out)
        self.assertIn("blocked: change failed", out)
        self.assertEqual(rc, 1, out)

    def test_unrelated_check_ignores_change_failure(self):
        cfg = self.repo.path / "openspec/config.yaml"
        cfg.write_text(cfg.read_text().replace('build: ""', 'build: "true"', 1))
        self.repo.change(1)
        self.repo.write("openspec/changes/other/proposal.md", "# O\n\nTier: 1\n")
        rc, lines, out = self.run_only("build")
        self.assertEqual(lines, ["PASS build"], out)
        self.assertEqual(rc, 0, out)

    def test_pr_tier_without_change_does_not_crash(self):
        event = self.repo.path / "event.json"
        event.write_text(json.dumps({"pull_request": {"body": "Tier: 1\n", "labels": []}}))
        ci = {"CI": "", "GITHUB_EVENT_PATH": str(event), "GITHUB_BASE_REF": ""}
        r = sh(self.repo.path, "scripts/check-change.sh", "--stage", "pr", env=ci)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("FAIL  change", r.stdout)
        self.assertIn("blocked: change failed", r.stdout)
        self.assertEqual(r.returncode, 1)

    def test_only_dedupes_names(self):
        self.approved_tier2()
        rc, lines, out = self.run_only("change, change")
        self.assertEqual(lines, ["PASS change"], out)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("Traceback", out)

    def test_only_rejects_unknown_names(self):
        for only in ("bogus", "", "change,,"):
            with self.subTest(only=only):
                rc, lines, out = self.run_only(only)
                self.assertEqual(rc, 2, out)
                self.assertNotIn("Traceback", out)
                self.assertIn("valid checks:", out)


class HookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Repo()

    def tearDown(self) -> None:
        self.repo.close()

    def test_guard_blocks_approval_line(self):
        hook = self.repo.path / ".claude/hooks/guard-approval.sh"
        blocked = sh(self.repo.path, str(hook), stdin=json.dumps(
            {"tool_name": "Edit", "tool_input": {"file_path": "p.md", "new_string": "Approved-by: me"}}))
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("human", blocked.stderr)
        allowed = sh(self.repo.path, str(hook), stdin=json.dumps(
            {"tool_name": "Write", "tool_input": {"file_path": "p.md", "content": "Tier: 1"}}))
        self.assertEqual(allowed.returncode, 0)

    def test_stop_hook_blocks_then_gives_up(self):
        hook = self.repo.path / ".claude/hooks/stop-check.sh"
        self.repo.write("AGENTS.md", "line\n" * 151)  # uncommitted and failing guide-size
        env = {"CLAUDE_PROJECT_DIR": str(self.repo.path), "TMPDIR": str(self.repo.path / "tmp")}
        (self.repo.path / "tmp").mkdir()
        payload = json.dumps({"session_id": "s1", "stop_hook_active": False})
        codes = [sh(self.repo.path, str(hook), env=env, stdin=payload).returncode for _ in range(4)]
        self.assertEqual(codes, [2, 2, 2, 0])

    def test_stop_hook_passes_on_clean_tree(self):
        hook = self.repo.path / ".claude/hooks/stop-check.sh"
        r = sh(self.repo.path, str(hook), env={"CLAUDE_PROJECT_DIR": str(self.repo.path)},
               stdin=json.dumps({"session_id": "s2"}))
        self.assertEqual(r.returncode, 0, r.stderr)


class GlobTest(unittest.TestCase):
    def test_globs(self):
        from check_change import matches
        self.assertTrue(matches("auth/login.py", ["**/auth/**"]))
        self.assertTrue(matches("svc/auth/login.py", ["**/auth/**"]))
        self.assertFalse(matches("svc/author.py", ["**/auth/**"]))
        self.assertTrue(matches("src/a/b.py", ["src/**"]))
        self.assertFalse(matches("src/a/b.py", ["src/*"]))
        self.assertTrue(matches("pkg/x.test.ts", ["**/*.test.*"]))


if __name__ == "__main__":
    unittest.main()
