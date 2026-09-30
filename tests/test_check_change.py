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
    def __init__(self, lifecycle: dict | None = None, base_files: dict | None = None) -> None:
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
        for rel, text in (base_files or {}).items():  # files that exist on the base branch
            (self.path / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.path / rel).write_text(text)
        (self.path / "openspec/changes/archive").mkdir(parents=True, exist_ok=True)
        (self.path / "openspec/specs").mkdir(parents=True, exist_ok=True)
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
        ci = {"CI": "", "LIFECYCLE_OVERRIDE": "", "GITHUB_EVENT_PATH": "", "GITHUB_BASE_REF": ""}
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


LEGACY = {"openspec/changes/legacy/proposal.md": "# Legacy\n\n## Why\n\nPredates the lifecycle.\n"}
GF_CHECKS = "change,risk-floor,approval,panel,tasks,evidence,artifacts-first,size"


class AdrNumberTest(unittest.TestCase):
    """ADR numbers in docs/decisions/ are unique; untouched old duplicates only warn locally."""

    def tearDown(self) -> None:
        self.repo.close()

    def gates(self, *args: str) -> tuple[int, str]:
        env = {"CI": "", "LIFECYCLE_OVERRIDE": "", "GITHUB_EVENT_PATH": "", "GITHUB_BASE_REF": ""}
        r = sh(self.repo.path, "scripts/check-change.sh", *(args or ("--only", "adr")), env=env)
        return r.returncode, r.stdout + r.stderr

    def test_duplicate_added_fails_every_stage(self):
        self.repo = Repo(base_files={"docs/decisions/0016-a.md": "# a\n"})
        self.repo.write("docs/decisions/0016-b.md", "# b\n")
        for args in (("--only", "adr"), ("--stage", "commit", "--quiet"), ("--stage", "hook", "--quiet"),
                     ("--stage", "pr")):
            with self.subTest(args=args):
                rc, out = self.gates(*args)
                self.assertIn("FAIL  adr", out)
                self.assertIn("0016-a.md", out)
                self.assertIn("0016-b.md", out)

    def test_preexisting_duplicate_warns_in_hook_fails_in_pr(self):
        self.repo = Repo(base_files={"docs/decisions/0005-a.md": "# a\n", "docs/decisions/0005-b.md": "# b\n"})
        self.repo.write("src/app.py", "x = 2\n")
        rc, out = self.gates("--stage", "hook", "--quiet")
        self.assertIn("WARN  adr", out)
        self.assertNotIn("FAIL  adr", out)
        rc, out = self.gates("--stage", "pr")
        self.assertIn("FAIL  adr", out)

    def test_renames_pass(self):
        self.repo = Repo(base_files={"docs/decisions/0016-a.md": "# a\n"})
        sh(self.repo.path, "git", "mv", "docs/decisions/0016-a.md", "docs/decisions/0016-b.md")
        self.repo.write("docs/decisions/0017-new.md", "# new\n")
        sh(self.repo.path, "git", "mv", "-f", "docs/decisions/0017-new.md", "docs/decisions/0018-new.md")
        rc, out = self.gates()
        self.assertIn("PASS  adr", out)

    def test_other_naming_ignored(self):
        self.repo = Repo()
        for name in ("adr-001.md", "README.md", "0007-x.MD", "sub/0007-y.md"):
            self.repo.write(f"docs/decisions/{name}", "x\n")
        rc, out = self.gates()
        self.assertIn("PASS  adr", out)
        self.repo.write("docs/decisions/0007-z.md", "x\n")
        rc, out = self.gates()
        self.assertIn("FAIL  adr", out)
        self.assertIn("0007-x.MD", out)


class YamlParseTest(unittest.TestCase):
    """Every YAML file must parse; the pre-commit config must also have a loadable shape."""

    def tearDown(self) -> None:
        self.repo.close()

    def gates(self, *args: str, ci: bool = False) -> tuple[int, str]:
        env = {"CI": "true" if ci else "", "LIFECYCLE_OVERRIDE": "", "GITHUB_EVENT_PATH": "", "GITHUB_BASE_REF": ""}
        r = sh(self.repo.path, "scripts/check-change.sh", *(args or ("--only", "yaml")), env=env)
        return r.returncode, r.stdout + r.stderr

    def test_broken_yaml_fails_with_line(self):
        self.repo = Repo()
        self.repo.write(".pre-commit-config.yaml",
                        "repos:\n- repo: local\n  hooks:\n  - id: x\n    name: gates (hook stage: tests)\n")
        rc, out = self.gates()
        self.assertIn("FAIL  yaml", out)
        self.assertIn(".pre-commit-config.yaml:5", out)

    def test_tags_and_multidoc_pass(self):
        self.repo = Repo()
        self.repo.write("cfn.yaml", "a: !Ref b\n---\nc: !GetAtt x.y\nd: !If [a, b]\ne: !Sub '${x}'\n")
        self.repo.write("vault.yml", "secret: !vault |\n  $ANSIBLE_VAULT;1.1;AES256\n  6162\n")
        rc, out = self.gates()
        self.assertIn("PASS  yaml", out)

    def test_constructor_and_nesting_errors_fail_per_file(self):
        self.repo = Repo()
        self.repo.write("bad_int.yaml", "a: !!int abc\n")
        self.repo.write("deep.yaml", "[" * 100000 + "]" * 100000 + "\n")
        (self.repo.path / "latin1.yaml").write_bytes(b"a: \xff\xfe\n")
        rc, out = self.gates()
        self.assertIn("FAIL  yaml", out)
        for name in ("bad_int.yaml", "deep.yaml", "latin1.yaml"):
            self.assertIn(name, out)
        self.assertNotIn("Traceback", out)

    def test_preexisting_broken_warns_in_hook_fails_in_pr(self):
        self.repo = Repo(base_files={"old.yaml": "a: [\n"})
        self.repo.write("src/app.py", "x = 2\n")  # the change touches something else
        rc, out = self.gates("--stage", "hook", "--quiet")
        self.assertIn("WARN  yaml", out)
        self.assertNotIn("FAIL  yaml", out)
        rc, out = self.gates("--stage", "pr")
        self.assertIn("FAIL  yaml", out)
        self.assertIn("old.yaml", out)

    def test_symlinks_skipped(self):
        self.repo = Repo()
        os.symlink("missing.yml", self.repo.path / "link.yml")
        self.repo.commit("dangling link")
        rc, out = self.gates()
        self.assertIn("PASS  yaml", out)

    def test_precommit_shape_checked(self):
        self.repo = Repo()
        for text in ("repos: {}\n", "repos:\n- repo: local\n", "repos:\n- repo: local\n  hooks:\n  - name: x\n"):
            with self.subTest(text=text):
                self.repo.write(".pre-commit-config.yaml", text)
                rc, out = self.gates()
                self.assertIn("FAIL  yaml", out)
                self.assertIn(".pre-commit-config.yaml", out)
        self.repo.write(".pre-commit-config.yaml", "repos:\n- repo: local\n  hooks:\n  - id: x\n")
        rc, out = self.gates()
        self.assertIn("PASS  yaml", out)

    def test_untracked_checked_locally_not_in_ci(self):
        self.repo = Repo()
        self.repo.write("new.yaml", "a: [\n")
        rc, out = self.gates()
        self.assertIn("FAIL  yaml", out)
        rc, out = self.gates(ci=True)
        self.assertIn("PASS  yaml", out)


class UntrackedSizeTest(unittest.TestCase):
    """Locally, size counts untracked files like git would; the hook stage only warns."""

    def setUp(self) -> None:
        self.repo = Repo()

    def tearDown(self) -> None:
        self.repo.close()

    def size(self, stage: str | None = None, ci: bool = False) -> tuple[int, str]:
        env = {"CI": "true" if ci else "", "LIFECYCLE_OVERRIDE": "", "GITHUB_EVENT_PATH": "", "GITHUB_BASE_REF": ""}
        args = ["--stage", stage, "--quiet"] if stage else ["--only", "size"]
        r = sh(self.repo.path, "scripts/check-change.sh", *args, env=env)
        return r.returncode, r.stdout + r.stderr

    def lines(self, n: int) -> str:
        return "".join(f"v{i} = {i}\n" for i in range(n))

    def test_size_counts_untracked_files(self):
        self.repo.write("src/new.py", self.lines(401))
        rc, out = self.size()
        self.assertIn("FAIL  size", out)
        self.assertIn("401 changed lines", out)

    def test_size_skips_excluded_ignored_binary_untracked(self):
        self.repo.write("tests/test_big.py", self.lines(500))
        self.repo.write(".gitignore", "scratch.log\n")
        self.repo.commit("ignore")
        self.repo.write("scratch.log", self.lines(500))
        (self.repo.path / "blob.bin").write_bytes(b"\x00" * 10 + b"\n" * 500)
        os.symlink("src/app.py", self.repo.path / "link.py")
        rc, out = self.size()
        self.assertIn("PASS  size", out)
        self.assertIn("2/400", out)  # .gitignore (1 line) + the symlink (1 line)

    def test_size_untracked_odd_names(self):
        self.repo.write("src/é new.py", self.lines(401))
        rc, out = self.size()
        self.assertIn("FAIL  size", out)
        self.assertNotIn("Traceback", out)

    def test_size_counts_last_line_without_newline(self):
        self.repo.write("src/a.py", self.lines(400) + "tail")
        rc, out = self.size()
        self.assertIn("401 changed lines", out)
        self.repo.write("src/a.py", "x\ry\r")  # CR-only: git counts 1
        rc, out = self.size()
        self.assertIn("1/400", out)

    def test_size_ci_ignores_untracked(self):
        self.repo.write("src/new.py", self.lines(500))
        rc, out = self.size(ci=True)
        self.assertIn("PASS  size", out)

    def test_hook_stage_warns_on_size(self):
        self.repo.write("src/new.py", self.lines(401))
        rc, out = self.size(stage="hook")
        self.assertIn("WARN  size", out)  # --quiet still shows the size warning
        self.assertEqual(rc, 0, out)
        rc, out = self.size(stage="pr")
        self.assertIn("FAIL  size", out)


class GrandfatherTest(unittest.TestCase):
    """In-flight changes that predate the lifecycle, bounded by what exists on the merge-base."""

    def tearDown(self) -> None:
        self.repo.close()

    def grandfathered_repo(self, **lifecycle) -> Repo:
        self.repo = Repo(lifecycle={"grandfathered_changes": ["legacy"], **lifecycle}, base_files=LEGACY)
        self.repo.write("openspec/changes/legacy/tasks.md", "- [ ] 1.1 still open\n")
        return self.repo

    def gates(self, only: str, body: str | None = None) -> tuple[int, str]:
        env = {"CI": "", "LIFECYCLE_OVERRIDE": "", "GITHUB_EVENT_PATH": "", "GITHUB_BASE_REF": ""}
        if body is not None:
            event = self.repo.path / "event.json"
            event.write_text(json.dumps({"pull_request": {"body": body, "labels": []}}))
            env["GITHUB_EVENT_PATH"] = str(event)
        r = sh(self.repo.path, "scripts/check-change.sh", "--only", only, env=env)
        return r.returncode, r.stdout + r.stderr

    def test_grandfathered_change_skips_change_gates(self):
        self.grandfathered_repo()
        rc, out = self.gates(GF_CHECKS)
        self.assertIn("WARN  change", out)
        self.assertIn("grandfathered", out)
        self.assertIn("PASS  risk-floor", out)
        for name in ("approval", "panel", "tasks", "evidence", "artifacts-first", "size"):
            self.assertRegex(out, rf"SKIP  {name}\s+grandfathered", out)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("Traceback", out)

    def test_grandfathered_risk_floor_warns(self):
        self.grandfathered_repo()
        self.repo.write("scripts/x.sh", "echo\n")
        rc, out = self.gates("change,risk-floor")
        self.assertRegex(out, r"WARN  risk-floor .*scripts/x.sh", out)
        self.assertEqual(rc, 0, out)

    def test_grandfathered_other_gates_still_run(self):
        self.grandfathered_repo(source_globs=["src/**"])
        import yaml
        cfg = self.repo.path / "openspec/config.yaml"
        data = yaml.safe_load(cfg.read_text())
        data["lifecycle"]["commands"]["test"] = "exit 3"
        cfg.write_text(yaml.safe_dump(data, sort_keys=False))
        self.repo.write("src/app.py", "x = 2\n")
        rc, out = self.gates("change,tests-with-code,commands")
        self.assertIn("FAIL  tests-with-code", out)
        self.assertIn("FAIL  commands", out)
        self.assertEqual(rc, 1, out)

    def test_grandfathered_needs_pr_declaration_in_ci(self):
        self.grandfathered_repo()
        rc, out = self.gates("change", body="Tier: 2\n")
        self.assertIn("FAIL  change", out)
        self.assertIn("Grandfathered: legacy", out)
        rc, out = self.gates("change,approval", body="Tier: 2\nGrandfathered: legacy\n")
        self.assertIn("WARN  change", out)  # the PR-body Tier is ignored for a grandfathered change
        self.assertIn("SKIP  approval", out)
        self.assertEqual(rc, 0, out)

    def test_grandfathered_archive_path(self):
        self.grandfathered_repo()
        self.repo.commit("work")
        sh(self.repo.path, "git", "mv", "openspec/changes/legacy", "openspec/changes/archive/2026-10-01-legacy")
        rc, out = self.gates("change")
        self.assertIn("WARN  change", out)
        self.assertIn("archive/2026-10-01-legacy", out)

    def test_new_change_reusing_id_not_grandfathered(self):
        self.repo = Repo(lifecycle={"grandfathered_changes": ["legacy"]})
        self.repo.write("openspec/changes/legacy/proposal.md", "# New\n\n## Why\n\nNew.\n")
        rc, out = self.gates("change")
        self.assertIn("FAIL  change", out)
        self.assertIn("listed, but not grandfathered", out)

    def test_pr_own_list_ignored(self):
        # (a) base has a lifecycle block without the key; the PR adds it.
        self.repo = Repo(base_files=LEGACY)
        cfg = self.repo.path / "openspec/config.yaml"
        cfg.write_text(cfg.read_text().replace("lifecycle:\n", "lifecycle:\n  grandfathered_changes: [legacy]\n", 1))
        self.repo.write("openspec/changes/legacy/tasks.md", "- [ ] open\n")
        rc, out = self.gates("change")
        self.assertIn("FAIL  change", out)
        self.repo.close()
        # (b) base has no lifecycle block at all; the PR adds the whole block.
        self.repo = Repo(base_files={**LEGACY, "openspec/config.yaml": "schema: spec-driven\n"})
        shutil.copy(TEMPLATE / "openspec/config.yaml", self.repo.path / "openspec/config.yaml")
        cfg = self.repo.path / "openspec/config.yaml"
        cfg.write_text(cfg.read_text().replace("lifecycle:\n", "lifecycle:\n  grandfathered_changes: [legacy]\n", 1))
        self.repo.write("openspec/changes/legacy/tasks.md", "- [ ] open\n")
        rc, out = self.gates("change")
        self.assertIn("FAIL  change", out)

    def test_malformed_list_grandfathers_nothing(self):
        for value in (None, "legacy", "leg"):
            with self.subTest(value=value):
                self.repo = Repo(lifecycle={"grandfathered_changes": value}, base_files=LEGACY)
                self.repo.write("openspec/changes/legacy/tasks.md", "- [ ] open\n")
                rc, out = self.gates("change")
                self.assertIn("FAIL  change", out)
                self.assertNotIn("Traceback", out)
                self.repo.close()
        self.repo = Repo()  # for tearDown

    def test_grandfathered_plus_second_change_fails(self):
        self.grandfathered_repo()
        self.repo.write("openspec/changes/other/proposal.md", "# O\n\nTier: 1\n")
        rc, out = self.gates("change")
        self.assertIn("FAIL  change", out)
        self.assertIn("one change per branch", out)

    def test_tier0_change_dir_fails(self):
        self.repo = Repo()
        self.repo.change(0)
        rc, out = self.gates("change")
        self.assertIn("FAIL  change", out)
        self.assertIn("tier 0 needs no OpenSpec change", out)
        rc, out = self.gates("change", body="Tier: 0\n")
        self.assertIn("tier 0 needs no OpenSpec change", out)


class OnlyTest(unittest.TestCase):
    """--only must not change results, hide a change failure, or crash on bad input."""

    def setUp(self) -> None:
        self.repo = Repo()

    def tearDown(self) -> None:
        self.repo.close()

    def run_only(self, only: str, env: dict | None = None) -> tuple[int, list[str], str]:
        ci = {"CI": "", "LIFECYCLE_OVERRIDE": "", "GITHUB_EVENT_PATH": "", "GITHUB_BASE_REF": ""}
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


def run_gates(repo: Repo, only: str, body: str | None = None) -> tuple[int, str]:
    """Like Repo.check, but optionally with a PR event body."""
    env = {"CI": "", "LIFECYCLE_OVERRIDE": "", "GITHUB_EVENT_PATH": "", "GITHUB_BASE_REF": ""}
    if body is not None:
        event = repo.path / "event.json"
        event.write_text(json.dumps({"pull_request": {"body": body, "labels": []}}))
        env["GITHUB_EVENT_PATH"] = str(event)
    r = sh(repo.path, "scripts/check-change.sh", "--only", only, env=env)
    return r.returncode, r.stdout + r.stderr


class ChangedPathsTest(unittest.TestCase):
    """Changed paths are read whole, and a rename lists both sides."""

    def tearDown(self) -> None:
        self.repo.close()

    def test_path_with_space_read_whole(self):
        for committed in (False, True):
            with self.subTest(committed=committed):
                self.repo = Repo()
                self.repo.write("scripts/a b.sh", "echo\n")
                if committed:
                    self.repo.commit("add")
                rc, out = self.repo.check("risk-floor")
                self.assertIn("'scripts/a b.sh'", out, out)
                self.assertNotIn("'scripts/a'", out, out)
                self.assertNotIn("'b.sh'", out, out)
                self.repo.close()
        self.repo = Repo()

    def test_rename_lists_both_sides(self):
        for committed in (False, True):
            with self.subTest(committed=committed):
                self.repo = Repo(base_files={"scripts/x.sh": "echo\n"})
                sh(self.repo.path, "git", "mv", "scripts/x.sh", "x.sh")
                if committed:
                    self.repo.commit("move")
                rc, out = self.repo.check("risk-floor")
                self.assertIn("FAIL  risk-floor", out, out)
                self.assertIn("scripts/x.sh", out, out)
                self.repo.close()
        self.repo = Repo()


ARCH = "openspec/changes/archive"


def legacy_archive(name: str, tasks: bool = True) -> dict:
    """An archived change that predates the lifecycle: no Tier line, one unticked task."""
    files = {f"{ARCH}/{name}/proposal.md": f"# {name}\n\n## Why\n\nOld.\n"}
    if tasks:
        files[f"{ARCH}/{name}/tasks.md"] = "## 1. Old\n\n- [ ] 1.1 Deferred\n"
    return files


TICKED = "## 1. Old\n\n- [x] 1.1 Deferred *(not done: ticked for validation)*\n"
NOT_COUNTED = "not counted: tasks.md-only edits"


class ArchiveTaskEditTest(unittest.TestCase):
    """tasks.md-only edits to archives on the merge-base are not the branch's change."""

    def tearDown(self) -> None:
        self.repo.close()

    def make(self, *names: str, **lifecycle) -> Repo:
        base: dict = {}
        for n in names:
            base.update(legacy_archive(n))
        self.repo = Repo(lifecycle=lifecycle or None, base_files=base)
        return self.repo

    def tick(self, name: str) -> None:
        self.repo.write(f"{ARCH}/{name}/tasks.md", TICKED)

    def assertCounted(self, name: str) -> None:
        """A counted legacy archive becomes the branch's change and fails for its missing Tier line."""
        rc, out = self.repo.check("change")
        self.assertIn("FAIL  change", out, out)
        self.assertIn(f"{ARCH}/{name}", out.split(NOT_COUNTED)[0], out)
        self.assertNotIn(NOT_COUNTED, out, out)

    # Exempt

    def test_tasks_only_edits_to_two_archives_pass(self):
        self.make("2026-01-01-old1", "2026-01-02-old2")
        self.tick("2026-01-01-old1")
        self.tick("2026-01-02-old2")
        self.repo.commit("tick legacy archives")
        rc, out = self.repo.check("change")
        self.assertIn("PASS  change", out, out)
        self.assertIn("tier 0", out, out)
        self.assertIn(NOT_COUNTED, out, out)
        self.assertIn("2026-01-01-old1", out, out)
        self.assertIn("2026-01-02-old2", out, out)
        self.assertEqual(rc, 0, out)

    def test_archive_edit_alongside_own_change(self):
        self.make("2026-01-01-old1")
        self.tick("2026-01-01-old1")
        self.repo.change(1)
        rc, out = self.repo.check("change")
        self.assertIn("PASS  change", out, out)
        self.assertIn("tier 1 (openspec/changes/add-thing)", out, out)
        self.assertIn(NOT_COUNTED, out, out)
        self.assertIn("2026-01-01-old1", out, out)

    def test_exempt_and_counted_archive(self):
        self.make("2026-01-01-old1", "2026-01-02-old2")
        self.tick("2026-01-01-old1")
        self.repo.write(f"{ARCH}/2026-01-02-old2/proposal.md", "# old2\n\nTier: 1\nApproved-by: A 2026-01-02\n")
        rc, out = self.repo.check("change")
        self.assertIn("PASS  change", out, out)
        self.assertIn(f"tier 1 ({ARCH}/2026-01-02-old2)", out, out)
        self.assertIn("2026-01-01-old1", out.split(NOT_COUNTED)[1], out)

    def test_note_survives_failure(self):
        self.make("2026-01-01-old1")
        self.tick("2026-01-01-old1")
        self.repo.change(1)
        self.repo.write("openspec/changes/other/proposal.md", "# O\n\nTier: 1\n")
        rc, out = self.repo.check("change")
        self.assertIn("FAIL  change", out, out)
        self.assertIn("one change per branch", out, out)
        self.assertNotIn("2026-01-01-old1", out.split(NOT_COUNTED)[0], out)
        self.assertIn("2026-01-01-old1", out.split(NOT_COUNTED)[1], out)

    def test_grandfathered_archive_tasks_only_is_exempt(self):
        self.make("2026-01-01-legacy", grandfathered_changes=["legacy"])
        self.tick("2026-01-01-legacy")
        rc, out = run_gates(self.repo, "change", body="Tier: 0\n")  # CI, no Grandfathered line
        self.assertIn("PASS  change", out, out)
        self.assertIn(NOT_COUNTED, out, out)
        self.assertEqual(rc, 0, out)

    def test_note_on_warn(self):
        base = {**LEGACY, **legacy_archive("2026-01-01-old1")}
        self.repo = Repo(lifecycle={"grandfathered_changes": ["legacy"]}, base_files=base)
        self.repo.write("openspec/changes/legacy/tasks.md", "- [ ] 1.1 still open\n")
        self.tick("2026-01-01-old1")
        rc, out = self.repo.check("change")
        self.assertIn("WARN  change", out, out)
        self.assertIn("grandfathered", out, out)
        self.assertIn("2026-01-01-old1", out.split(NOT_COUNTED)[1], out)

    # Counted, as before

    def test_archive_other_file_counts(self):
        self.make("2026-01-01-old1")
        self.tick("2026-01-01-old1")
        self.repo.write(f"{ARCH}/2026-01-01-old1/proposal.md", "# old1\n\n## Why\n\nRewritten.\n")
        self.assertCounted("2026-01-01-old1")

    def test_file_moved_out_of_archive_counts(self):
        self.make("2026-01-01-old1")
        self.tick("2026-01-01-old1")
        self.repo.commit("tick")
        sh(self.repo.path, "git", "mv", f"{ARCH}/2026-01-01-old1/proposal.md", "moved.md")
        rc, out = self.repo.check("change")
        self.assertIn("FAIL  change", out, out)
        self.assertNotIn(NOT_COUNTED, out, out)

    def test_tasks_added_deleted_moved_or_symlinked_counts(self):
        name, d = "2026-01-01-old1", f"{ARCH}/2026-01-01-old1"
        for case in ("added", "deleted", "moved", "symlinked"):
            with self.subTest(case=case):
                base = legacy_archive(name, tasks=case != "added")
                self.repo = Repo(base_files=base)
                p = self.repo.path / d / "tasks.md"
                if case == "added":
                    self.repo.write(f"{d}/tasks.md", TICKED)
                elif case == "deleted":
                    p.unlink()
                elif case == "moved":
                    sh(self.repo.path, "git", "mv", f"{d}/tasks.md", f"{d}/notes.md")
                else:
                    p.unlink()
                    p.symlink_to("proposal.md")
                self.repo.commit(case)
                rc, out = self.repo.check("change")
                self.assertNotIn(NOT_COUNTED, out, out)
                self.assertIn("FAIL  change", out, out)
                self.repo.close()
        self.repo = Repo()  # for tearDown

    def test_hidden_name_beside_tasks_counts(self):
        for committed in (False, True):  # untracked, then committed
            with self.subTest(committed=committed):
                self.make("2026-01-01-old1")
                self.tick("2026-01-01-old1")
                self.repo.commit("tick")
                self.repo.write(f"{ARCH}/2026-01-01-old1/tasks.md x.txt", "smuggled\n")
                if committed:
                    self.repo.commit("hide")
                self.assertCounted("2026-01-01-old1")
                self.repo.close()
        self.repo = Repo()

    def test_non_archive_name_never_exempt(self):
        for name in ("old-thing", "2026-01-01-Old", "2026-01-01-a_b"):
            with self.subTest(name=name):
                self.make(name)
                self.tick(name)
                self.assertCounted(name)
                self.repo.close()
        self.repo = Repo()

    def test_new_archive_counts(self):
        self.make("2026-01-01-old1")
        self.repo.write(f"{ARCH}/2026-10-01-add-thing/proposal.md", "# Add\n\nTier: 1\nApproved-by: A 2026-10-01\n")
        rc, out = self.repo.check("change")
        self.assertIn(f"PASS  change           tier 1 ({ARCH}/2026-10-01-add-thing)", out, out)
        self.assertNotIn(NOT_COUNTED, out, out)

    def test_moved_in_flight_change_plus_exempt_edit(self):
        base = legacy_archive("2026-01-01-old1")
        base["openspec/changes/add-thing/proposal.md"] = "# Add\n\nTier: 1\nApproved-by: A 2026-10-01\n"
        self.repo = Repo(base_files=base)
        sh(self.repo.path, "git", "mv", "openspec/changes/add-thing", f"{ARCH}/2026-10-01-add-thing")
        self.tick("2026-01-01-old1")
        rc, out = self.repo.check("change")
        self.assertIn(f"PASS  change           tier 1 ({ARCH}/2026-10-01-add-thing)", out, out)
        self.assertIn("2026-01-01-old1", out.split(NOT_COUNTED)[1], out)

    def test_pr_tier1_with_only_exempt_edits_fails(self):
        self.make("2026-01-01-old1")
        self.tick("2026-01-01-old1")
        rc, out = run_gates(self.repo, "change", body="Tier: 1\n")
        self.assertIn("FAIL  change", out, out)
        self.assertIn("tier 1 needs an OpenSpec change", out, out)
        self.assertIn(NOT_COUNTED, out, out)

    def test_no_base_no_exemption(self):
        self.make("2026-01-01-old1")
        self.tick("2026-01-01-old1")
        self.repo.commit("tick")
        sh(self.repo.path, "git", "branch", "-D", "main")
        self.assertCounted("2026-01-01-old1")


def lines(n: int, tag: str = "x") -> str:
    return "".join(f"{tag}{i} = {i}\n" for i in range(n))


class GatePathsTest(unittest.TestCase):
    """artifacts-first and size read git paths exactly; size counts a move by where it lands."""

    def tearDown(self) -> None:
        self.repo.close()

    def size(self) -> str:
        rc, out = self.repo.check("size")
        return out

    # artifacts-first

    def test_plan_commit_with_space_and_non_ascii_passes(self):
        self.repo = Repo()
        self.repo.change(2, panel="No findings.\n")
        self.repo.write("openspec/changes/add-thing/a b.md", "notes\n")
        self.repo.write("openspec/changes/add-thing/é.md", "notes\n")
        self.repo.commit("artifacts")
        self.repo.write("src/app.py", "x = 2\n")
        self.repo.commit("code")
        rc, out = self.repo.check("artifacts-first")
        self.assertIn("PASS  artifacts-first", out, out)

    def test_stray_file_with_space_is_named(self):
        self.repo = Repo(base_files=legacy_archive("2026-01-01-old1"))
        self.repo.change(2, panel="No findings.\n")
        self.repo.write(f"{ARCH}/2026-01-01-old1/tasks.md", TICKED)  # exempt archive edit, allowed
        self.repo.write("src/a b.py", "x = 1\n")
        self.repo.commit("artifacts plus a stray file")
        rc, out = self.repo.check("artifacts-first")
        self.assertIn("FAIL  artifacts-first", out, out)
        self.assertIn("'src/a b.py'", out, out)

    # size

    def test_non_ascii_path_matches_size_exclusion(self):
        self.repo = Repo(lifecycle={"size_budget": 10})
        self.repo.write("docs/é.md", lines(50))
        self.repo.commit("doc")
        self.assertIn("PASS  size             0/10", self.size())

    def test_move_from_excluded_into_source_counts_whole_file(self):
        self.repo = Repo(lifecycle={"size_budget": 10}, base_files={"tests/big.py": lines(50)})
        sh(self.repo.path, "git", "mv", "tests/big.py", "src/big.py")
        self.repo.write("src/big.py", lines(50) + "y = 2\n")
        self.repo.commit("move into source")
        out = self.size()
        self.assertIn("FAIL  size             51 changed lines", out, out)

    def test_move_from_source_into_excluded_counts_old_file(self):
        self.repo = Repo(lifecycle={"size_budget": 10}, base_files={"lib/a.py": lines(50)})
        (self.repo.path / "tests").mkdir()
        sh(self.repo.path, "git", "mv", "lib/a.py", "tests/a.py")
        self.repo.commit("move out of source")
        out = self.size()
        self.assertIn("FAIL  size             50 changed lines", out, out)

    def test_move_with_edits_counts_delta(self):
        self.repo = Repo(lifecycle={"size_budget": 10}, base_files={"lib/a.py": lines(20)})
        sh(self.repo.path, "git", "mv", "lib/a.py", "lib/b.py")
        self.repo.write("lib/b.py", lines(20) + lines(3, "y"))
        self.repo.commit("move and edit")
        self.assertIn("PASS  size             3/10", self.size())

    def test_rename_detection_ignores_config(self):
        self.repo = Repo(lifecycle={"size_budget": 10}, base_files={"lib/a.py": lines(8)})
        sh(self.repo.path, "git", "config", "diff.renames", "false")
        sh(self.repo.path, "git", "mv", "lib/a.py", "lib/b.py")
        self.repo.commit("pure move")
        self.assertIn("PASS  size             0/10", self.size())

    def test_text_attr_move_into_excluded_never_negative(self):
        data = "".join(f"row{i}\0\n" for i in range(30))
        self.repo = Repo(lifecycle={"size_budget": 100},
                         base_files={".gitattributes": "*.dat diff\n", "lib/n.dat": data})
        (self.repo.path / "tests").mkdir()
        sh(self.repo.path, "git", "mv", "lib/n.dat", "tests/n.dat")
        self.repo.write("lib/x.py", lines(3))
        self.repo.commit("move a text-diffed file out, add code")
        self.assertIn("PASS  size             33/100", self.size())

    def test_pure_move_in_source_costs_nothing(self):
        self.repo = Repo(lifecycle={"size_budget": 10}, base_files={"lib/a.py": lines(8)})
        sh(self.repo.path, "git", "mv", "lib/a.py", "lib/b.py")
        self.repo.commit("pure move")
        self.assertIn("PASS  size             0/10", self.size())

    def test_binary_move_then_edit_counts_edit(self):
        self.repo = Repo(lifecycle={"size_budget": 10})
        (self.repo.path / "lib").mkdir()
        (self.repo.path / "lib/b.bin").write_bytes(bytes(range(256)) * 40)
        self.repo.commit("binary")
        sh(self.repo.path, "git", "branch", "-f", "main", "HEAD")  # the binary is on the base
        sh(self.repo.path, "git", "mv", "lib/b.bin", "lib/c.bin")
        self.repo.write("lib/x.py", lines(3))
        self.repo.commit("move binary, add code")
        self.assertIn("PASS  size             3/10", self.size())

    def test_empty_diff_counts_zero(self):
        self.repo = Repo(lifecycle={"size_budget": 10})
        self.assertIn("PASS  size             0/10", self.size())


if __name__ == "__main__":
    unittest.main()
