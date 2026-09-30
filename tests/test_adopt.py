"""Unit tests for scripts/lib/adopt.py: proposals, risk report and the validated undo."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEMPLATE / "scripts/lib"))

import adopt  # noqa: E402

TPL_SETTINGS = json.loads((TEMPLATE / ".claude/settings.json").read_text())
ALL_HOOKS_OK = {"guard-approval": True, "stop-check": True}


def hook_commands(data: dict, event: str) -> list[str]:
    return [h["command"] for g in data.get("hooks", {}).get(event, []) for h in g["hooks"]]


class SettingsProposalTest(unittest.TestCase):
    def test_proposed_settings_merge(self):
        target = {"permissions": {"allow": ["Bash(make help)"], "deny": ["Read(./.env)"]},
                  "enabledPlugins": {"superpowers@claude-plugins-official": True}}
        data, reason = adopt.propose_settings(json.dumps(target), TPL_SETTINGS, ALL_HOOKS_OK)
        self.assertIsNone(reason)
        self.assertEqual(data["enabledPlugins"], target["enabledPlugins"])
        self.assertEqual(data["permissions"]["allow"], ["Bash(make help)"])  # template allows not added
        self.assertIn("Read(./.env)", data["permissions"]["deny"])
        for rule in TPL_SETTINGS["permissions"]["deny"]:
            self.assertIn(rule, data["permissions"]["deny"])
        self.assertIs(data["sandbox"]["enabled"], True)
        self.assertEqual(len(hook_commands(data, "Stop")), 1)
        self.assertEqual(len(hook_commands(data, "PreToolUse")), 1)

    def test_hooks_already_referenced(self):
        target = {"hooks": {"Stop": [{"hooks": [{"type": "command",
                  "command": '"$CLAUDE_PROJECT_DIR"/.claude/hooks/stop-check.sh'}]}]}}
        data, _ = adopt.propose_settings(json.dumps(target), TPL_SETTINGS, ALL_HOOKS_OK)
        self.assertEqual(len(hook_commands(data, "Stop")), 1)
        again, _ = adopt.propose_settings(json.dumps(data), TPL_SETTINGS, ALL_HOOKS_OK)
        self.assertEqual(again, data)  # re-proposing adds nothing

    def test_differing_hook_not_wired(self):
        data, _ = adopt.propose_settings("{}", TPL_SETTINGS, {"guard-approval": True, "stop-check": False})
        self.assertEqual(hook_commands(data, "Stop"), [])
        self.assertEqual(len(hook_commands(data, "PreToolUse")), 1)

    def test_sandbox_disabled_kept(self):
        data, _ = adopt.propose_settings('{"sandbox": {"enabled": false}}', TPL_SETTINGS, ALL_HOOKS_OK)
        self.assertIs(data["sandbox"]["enabled"], False)

    def test_jsonc_settings_not_proposed(self):
        for text in ('{/* c */}', '{"a": 1,}', '[]', '{"permissions": []}',
                     '{"permissions": {"deny": "Bash(x)"}}', '{"sandbox": true}'):
            with self.subTest(text=text):
                data, reason = adopt.propose_settings(text, TPL_SETTINGS, ALL_HOOKS_OK)
                self.assertIsNone(data)
                self.assertTrue(reason)


class RiskTest(unittest.TestCase):
    def test_risk_report(self):
        data = {"permissions": {"defaultMode": "bypassPermissions", "allow": ["Bash", "Edit(*)", "Bash(make x)"]},
                "disableAllHooks": True, "sandbox": {"enabled": False, "allowUnsandboxedCommands": True}}
        text = "\n".join(adopt.risks(data, differing_hooks=["stop-check"]))
        for needle in ("bypassPermissions", "disableAllHooks", "allowUnsandboxedCommands",
                       "sandbox.enabled", "Bash", "Edit(*)", "stop-check"):
            self.assertIn(needle, text)
        self.assertNotIn("Bash(make x)", text)
        self.assertEqual(adopt.risks({}, differing_hooks=[]), [])

    def test_clean_strips_control_chars(self):
        self.assertEqual(adopt.clean("a\x1b[31mb\x07"), "a?[31mb?")


class ConfigSnippetTest(unittest.TestCase):
    TPL = (TEMPLATE / "openspec/config.yaml").read_text()
    LIFECYCLE = {"commands": {"test": "make test"}, "managed_paths": ["scripts/check-change.sh"]}

    def test_config_snippet_only_missing_sections(self):
        target = "schema: spec-driven\nrules:\n  proposal: [x]\n# trailing comment"
        snippet, missing, reason = adopt.config_snippet(target, self.TPL, self.LIFECYCLE)
        self.assertIsNone(reason)
        parsed = adopt.yaml.safe_load(snippet)
        self.assertIn("lifecycle", parsed)
        self.assertIn("operations", parsed)
        self.assertNotIn("rules", parsed)
        self.assertEqual(parsed["lifecycle"]["commands"]["test"], "make test")
        self.assertEqual(missing, [])

    def test_existing_lifecycle_lists_missing_keys(self):
        target = "schema: spec-driven\ncontext: x\nrules: {}\noperations: {}\nlifecycle:\n  commands: {}\n"
        snippet, missing, _ = adopt.config_snippet(target, self.TPL, self.LIFECYCLE)
        self.assertEqual(snippet, "")
        self.assertIn("managed_paths", missing)

    def test_invalid_config_not_proposed(self):
        snippet, missing, reason = adopt.config_snippet("a: [\n", self.TPL, self.LIFECYCLE)
        self.assertIsNone(snippet)
        self.assertTrue(reason)


class GuideBlockTest(unittest.TestCase):
    def test_guide_blocks(self):
        agents, claude = adopt.guide_blocks()
        lines = agents.strip().splitlines()
        self.assertEqual(lines[0], adopt.START)
        self.assertEqual(lines[-1], adopt.END)
        self.assertLessEqual(len(lines) - 2, 12)
        self.assertIn("lifecycle gates win", agents)
        self.assertIn("docs/agent-lifecycle.md", agents)
        self.assertIn("@docs/agent-lifecycle.md", claude)
        self.assertIn("lifecycle gates win", claude)


class UndoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        (self.root / adopt.FOLDER).mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def undo(self, lines: list[str]) -> subprocess.CompletedProcess:
        (self.root / adopt.FOLDER / "MANIFEST").write_text("".join(f"{line}\n" for line in lines))
        return subprocess.run([sys.executable, str(TEMPLATE / "scripts/lib/adopt.py"), "undo",
                               "--target", str(self.root)], capture_output=True, text=True)

    def test_undo_rejects_tampered_manifest(self):
        (self.root / "keep.txt").write_text("x")
        outside = Path(self.tmp.name) / "outside.txt"
        outside.write_text("x")
        for bad in ("..", "../outside.txt", "/etc", ".git", "a/../keep.txt", str(outside), "./keep.txt"):
            with self.subTest(line=bad):
                r = self.undo(["keep.txt", bad])
                self.assertNotEqual(r.returncode, 0)
                self.assertTrue((self.root / "keep.txt").exists(), "removed despite a bad line")
                self.assertTrue(outside.exists())

    def test_undo_keeps_user_files(self):
        (self.root / "d/sub").mkdir(parents=True)
        (self.root / "d/sub/ours.txt").write_text("x")
        (self.root / "d/user.txt").write_text("mine")
        r = self.undo(["d", "d/sub", "d/sub/ours.txt"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.root / "d/sub").exists())
        self.assertTrue((self.root / "d/user.txt").exists())
        self.assertFalse((self.root / adopt.FOLDER).exists())

    def test_realpath_sibling_prefix_rejected(self):
        sibling = Path(str(self.root) + "-evil")
        sibling.mkdir()
        self.assertFalse(adopt.inside(os.path.realpath(self.root), sibling / "x"))
        self.assertTrue(adopt.inside(os.path.realpath(self.root), self.root / "a/b"))


if __name__ == "__main__":
    unittest.main()
