#!/usr/bin/env python3
"""Lifecycle gates. The same code runs in CI, in pre-commit and in the agent's Stop hook.

Stages pick which checks run:
  commit  fast, file-only checks (no stack commands)
  hook    what an agent must pass before it may stop: commit checks + stack commands
  pr      everything, including gates that only make sense at merge time

Configuration lives under `lifecycle:` in openspec/config.yaml.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("check-change: PyYAML is required (pip install pyyaml)")

ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                           text=True, check=True).stdout.strip())
CHANGES = "openspec/changes"
ARCHIVE = "openspec/changes/archive"

STAGES = {
    "commit": ["openspec", "workflows", "skills-sync", "guide-size", "change", "risk-floor"],
    "hook": ["openspec", "workflows", "skills-sync", "guide-size", "change", "risk-floor",
             "evidence", "commands"],
    "pr": ["openspec", "workflows", "skills-sync", "guide-size", "change", "risk-floor",
           "approval", "panel", "tasks", "evidence", "artifacts-first", "tests-with-code",
           "size", "commands", "audit"],
}


# ---------------------------------------------------------------- helpers

def git(*args: str, check: bool = True) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          check=check).stdout


def glob_re(pattern: str) -> re.Pattern[str]:
    """Git-style glob: `**/` spans directories, `*` stays within one."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + r"\Z")


def matches(path: str, patterns: list[str]) -> bool:
    return any(glob_re(p).match(path) for p in patterns)


@dataclass
class Context:
    cfg: dict
    base: str | None
    changed: list[str]
    pr_body: str = ""
    labels: set[str] = field(default_factory=set)
    in_ci: bool = False
    change_dir: Path | None = None
    tier: int | None = None
    overrides: set[str] = field(default_factory=set)


def load_config() -> dict:
    path = ROOT / "openspec/config.yaml"
    data = yaml.safe_load(path.read_text()) if path.exists() else {}
    return (data or {}).get("lifecycle") or {}


def resolve_base(explicit: str | None) -> str | None:
    candidates = [explicit] if explicit else []
    if os.environ.get("GITHUB_BASE_REF"):
        candidates.append("origin/" + os.environ["GITHUB_BASE_REF"])
    candidates += ["origin/main", "main"]
    for ref in candidates:
        if ref and subprocess.run(["git", "rev-parse", "--verify", "-q", ref], cwd=ROOT,
                                  capture_output=True).returncode == 0:
            mb = git("merge-base", ref, "HEAD", check=False).strip()
            if mb:
                return mb
    return None


def changed_files(base: str | None) -> list[str]:
    files: set[str] = set()
    if base:
        files.update(git("diff", "--name-only", base).split())
    else:  # no base (fresh repo): everything tracked counts as changed
        files.update(git("ls-files").split())
    files.update(git("diff", "--name-only", "--cached").split())
    files.update(git("ls-files", "--others", "--exclude-standard").split())
    return sorted(f for f in files if f)


def pr_event() -> tuple[str, set[str]]:
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path or not Path(path).exists():
        return "", set()
    pr = json.loads(Path(path).read_text()).get("pull_request") or {}
    return pr.get("body") or "", {label["name"] for label in pr.get("labels", [])}


def item_blocks(text: str) -> list[tuple[str, str]]:
    """Split a markdown checklist into (mark, block) pairs; block includes indented lines."""
    blocks, current = [], None
    for line in text.splitlines():
        m = re.match(r"^\s*[-*]\s*\[([ xX])\]\s", line)
        if m:
            current = [m.group(1).lower(), line]
            blocks.append(current)
        elif current and (line.startswith((" ", "\t")) and line.strip()):
            current[1] += "\n" + line
        else:
            current = None
    return [(mark, block) for mark, block in blocks]


# ---------------------------------------------------------------- checks
# Each check returns (status, message); status is PASS, FAIL, WARN or SKIP.

def check_change(ctx: Context):
    dirs = set()
    for f in ctx.changed:
        parts = f.split("/")
        if f.startswith(ARCHIVE + "/") and len(parts) > 4:
            dirs.add("/".join(parts[:4]))
        elif f.startswith(CHANGES + "/") and len(parts) > 3 and parts[2] != "archive":
            dirs.add("/".join(parts[:3]))
    dirs = {d for d in dirs if (ROOT / d).is_dir()}
    if len(dirs) > 1:
        return "FAIL", f"one change per branch; found {sorted(dirs)}"
    if dirs:
        ctx.change_dir = ROOT / dirs.pop()
        proposal = ctx.change_dir / "proposal.md"
        m = re.search(r"^Tier:\s*([012])\b", proposal.read_text(), re.M) if proposal.exists() else None
        if not m:
            return "FAIL", f"{proposal.relative_to(ROOT)} must declare `Tier: 0|1|2`"
        ctx.tier = int(m.group(1))
    body_tier = re.search(r"^\s*Tier:\s*([012])\b", ctx.pr_body, re.M)
    if body_tier:
        if ctx.tier is not None and int(body_tier.group(1)) != ctx.tier:
            return "FAIL", f"PR says tier {body_tier.group(1)}, proposal says tier {ctx.tier}"
        ctx.tier = int(body_tier.group(1))
    if ctx.tier is None:
        ctx.tier = 0
    if ctx.tier >= 1 and ctx.change_dir is None:
        return "FAIL", f"tier {ctx.tier} needs an OpenSpec change under {CHANGES}/"
    where = ctx.change_dir.relative_to(ROOT) if ctx.change_dir else "no change dir"
    return "PASS", f"tier {ctx.tier} ({where})"


def check_risk_floor(ctx: Context):
    risky = [f for f in ctx.changed if matches(f, ctx.cfg.get("high_risk_paths", []))]
    if risky and (ctx.tier or 0) < 2:
        return "FAIL", f"touches high-risk paths, so tier must be 2: {risky[:5]}"
    return "PASS", f"{len(risky)} high-risk path(s) touched"


def check_approval(ctx: Context):
    if (ctx.tier or 0) == 0:
        return "SKIP", "tier 0"
    text = (ctx.change_dir / "proposal.md").read_text()
    if not re.search(r"^Approved-by:\s*\S+", text, re.M):
        return "FAIL", "proposal.md has no `Approved-by:` line from the human"
    return "PASS", "approval recorded"


def check_panel(ctx: Context):
    if ctx.change_dir is None:
        return "SKIP", "no change"
    panel = ctx.change_dir / "panel.md"
    if not panel.exists():
        return ("FAIL", "tier 2 needs panel.md") if ctx.tier == 2 else ("SKIP", "no panel.md")
    open_critical = [b for mark, b in item_blocks(panel.read_text())
                     if mark == " " and re.search(r"\[critical\]", b, re.I)]
    if open_critical:
        return "FAIL", f"{len(open_critical)} open critical finding(s) in panel.md"
    return "PASS", "no open critical findings"


def check_tasks(ctx: Context):
    if ctx.change_dir is None:
        return "SKIP", "no change"
    tasks = ctx.change_dir / "tasks.md"
    if not tasks.exists():
        return "FAIL", "change has no tasks.md"
    open_items = [b for mark, b in item_blocks(tasks.read_text()) if mark == " "]
    if open_items:
        return "FAIL", f"{len(open_items)} unticked task(s) in tasks.md"
    return "PASS", "all tasks ticked"


def check_evidence(ctx: Context):
    if ctx.change_dir is None or not (ctx.change_dir / "tasks.md").exists():
        return "SKIP", "no tasks.md"
    missing = [b.splitlines()[0].strip() for mark, b in item_blocks((ctx.change_dir / "tasks.md").read_text())
               if mark == "x" and not re.search(r"evidence:", b, re.I)]
    if missing:
        return "FAIL", f"ticked without `Evidence:`: {missing[:3]}"
    return "PASS", "every ticked task cites evidence"


def check_artifacts_first(ctx: Context):
    if (ctx.tier or 0) == 0 or not ctx.base:
        return "SKIP", "tier 0 or no base"
    commits = git("rev-list", "--topo-order", "--reverse", "--no-merges", f"{ctx.base}..HEAD").split()
    if not commits:
        return "SKIP", "no commits on branch"
    first = git("diff-tree", "--no-commit-id", "--name-only", "-r", commits[0]).split()
    stray = [f for f in first if not f.startswith(CHANGES + "/")]
    if stray:
        return "FAIL", f"first commit must hold only the approved artifacts; also has {stray[:3]}"
    return "PASS", "plan pinned before code"


def overridden(ctx: Context, key: str) -> bool:
    label = (ctx.cfg.get("override_labels") or {}).get(key)
    return key in ctx.overrides or (label is not None and label in ctx.labels)


def check_tests_with_code(ctx: Context):
    src_globs, test_globs = ctx.cfg.get("source_globs") or [], ctx.cfg.get("test_globs") or []
    if not src_globs:
        return "WARN", "lifecycle.source_globs is empty; gate not active"
    tests = [f for f in ctx.changed if matches(f, test_globs)]
    source = [f for f in ctx.changed if matches(f, src_globs) and f not in tests]
    if source and not tests:
        if overridden(ctx, "tests_with_code"):
            return "WARN", "source changed without tests (overridden)"
        return "FAIL", f"source changed but no test changed: {source[:3]}"
    return "PASS", f"{len(source)} source / {len(tests)} test file(s)"


def check_size(ctx: Context):
    if not ctx.base:
        return "SKIP", "no base to diff against"
    budget = int(ctx.cfg.get("size_budget") or 0)
    if not budget:
        return "SKIP", "no size_budget"
    exclude = (ctx.cfg.get("size_exclude") or []) + (ctx.cfg.get("test_globs") or []) + ["openspec/**"]
    total = 0
    for line in git("diff", "--numstat", ctx.base).splitlines():
        added, deleted, path = line.split("\t", 2)
        if added == "-" or matches(path, exclude):
            continue
        total += int(added) + int(deleted)
    if total > budget:
        if overridden(ctx, "size_budget"):
            return "WARN", f"{total} changed lines > {budget} (overridden)"
        return "FAIL", f"{total} changed lines > budget {budget}; split the change"
    return "PASS", f"{total}/{budget} changed lines"


def check_workflows(ctx: Context):
    wf_dir = ROOT / ".github/workflows"
    problems = []
    for wf in sorted(list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml"))):
        text = wf.read_text()
        for ref in re.findall(r"^\s*-?\s*uses:\s*['\"]?([^\s'\"#]+)", text, re.M):
            if ref.startswith("./") or re.search(r"@[0-9a-f]{40}$", ref) \
                    or re.match(r"docker://.+@sha256:[0-9a-f]{64}$", ref):
                continue
            problems.append(f"{wf.name}: `{ref}` not pinned to a full SHA")
        if "permissions" not in (yaml.safe_load(text) or {}):
            problems.append(f"{wf.name}: no top-level `permissions:`")
    return ("FAIL", "; ".join(problems)) if problems else ("PASS", "actions pinned, token scoped")


def tree(path: Path) -> dict[str, bytes]:
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}


def check_skills_sync(ctx: Context):
    src, dst = ROOT / ".claude/skills", ROOT / ".agents/skills"
    if not src.exists():
        return "SKIP", "no .claude/skills"
    ours = {p.name for p in src.iterdir() if p.is_dir() and not p.name.startswith("openspec-")}
    theirs = {p.name for p in dst.iterdir() if p.is_dir() and not p.name.startswith("openspec-")} \
        if dst.exists() else set()
    drift = sorted(n for n in ours | theirs
                   if n not in ours or n not in theirs or tree(src / n) != tree(dst / n))
    if drift:
        return "FAIL", f".agents/skills out of sync for {drift}; run scripts/sync-skills.sh"
    return "PASS", f"{len(ours)} skill(s) in sync"


def check_guide_size(ctx: Context):
    guide = ROOT / "AGENTS.md"
    if not guide.exists():
        return "FAIL", "AGENTS.md missing"
    limit = int(ctx.cfg.get("agent_guide_max_lines") or 150)
    n = len(guide.read_text().splitlines())
    return ("FAIL" if n > limit else "PASS"), f"AGENTS.md {n}/{limit} lines"


def check_openspec(ctx: Context):
    if not shutil.which("openspec"):
        return ("FAIL" if ctx.in_ci else "WARN"), "openspec CLI not installed"
    for args in (["validate", "--all", "--strict", "--no-interactive"],
                 ["validate", "--archived", "--no-interactive"]):
        r = subprocess.run(["openspec", *args], cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            return "FAIL", f"openspec {' '.join(args)}:\n{(r.stdout + r.stderr).strip()}"
    return "PASS", "openspec validate --strict"


def run_commands(ctx: Context, names: list[str]):
    cmds = ctx.cfg.get("commands") or {}
    ran, empty = [], []
    for name in names:
        cmd = (cmds.get(name) or "").strip()
        if not cmd:
            empty.append(name)
            continue
        r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-30:])
            return "FAIL", f"`{cmd}` exited {r.returncode}:\n{tail}"
        ran.append(name)
    if empty and not ran:
        return "WARN", f"no commands configured for {empty} in lifecycle.commands"
    return "PASS", f"ran {ran}" + (f"; not configured: {empty}" if empty else "")


CHECKS = {
    "change": check_change,
    "risk-floor": check_risk_floor,
    "approval": check_approval,
    "panel": check_panel,
    "tasks": check_tasks,
    "evidence": check_evidence,
    "artifacts-first": check_artifacts_first,
    "tests-with-code": check_tests_with_code,
    "size": check_size,
    "workflows": check_workflows,
    "skills-sync": check_skills_sync,
    "guide-size": check_guide_size,
    "openspec": check_openspec,
    "commands": lambda ctx: run_commands(ctx, ["lint", "typecheck", "test"]),
    "audit": lambda ctx: run_commands(ctx, ["audit"]),
    "build": lambda ctx: run_commands(ctx, ["build"]),  # release workflow only
}


# Checks that read the tier or change directory `change` resolves.
NEEDS_CHANGE = {"risk-floor", "approval", "panel", "tasks", "evidence", "artifacts-first"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", choices=STAGES, default="pr")
    ap.add_argument("--only", help="comma-separated checks to run")
    ap.add_argument("--base", help="base ref (default: PR base, origin/main or main)")
    ap.add_argument("--quiet", action="store_true", help="print failures only")
    args = ap.parse_args()

    if args.only is not None:
        names = list(dict.fromkeys(n.strip() for n in args.only.split(",")))
        unknown = [n for n in names if n not in CHECKS]
        if unknown or not names:
            print(f"check-change: unknown check {unknown or ['']}; valid checks: {', '.join(CHECKS)}",
                  file=sys.stderr)
            return 2
    else:
        names = STAGES[args.stage]

    body, labels = pr_event()
    ctx = Context(cfg=load_config(), base=resolve_base(args.base), changed=[], pr_body=body,
                  labels=labels, in_ci=bool(os.environ.get("CI")))
    ctx.changed = changed_files(ctx.base)
    # Local override, e.g. LIFECYCLE_OVERRIDE="size_budget: generated client"; CI uses PR labels.
    if os.environ.get("LIFECYCLE_OVERRIDE") and not ctx.in_ci:
        ctx.overrides = {os.environ["LIFECYCLE_OVERRIDE"].split(":")[0].strip()}

    # Resolve the change once, up front, so no check's result depends on --only order.
    change_result = check_change(ctx)
    change_failed = change_result[0] == "FAIL"
    if change_failed and "change" not in names and NEEDS_CHANGE.intersection(names):
        names = ["change", *names]  # a failure that blocks requested checks is never hidden
    failed = False
    for name in names:
        if name == "change":
            status, msg = change_result
        elif change_failed and name in NEEDS_CHANGE:
            status, msg = "SKIP", "blocked: change failed"
        else:
            status, msg = CHECKS[name](ctx)
        failed |= status == "FAIL"
        if not args.quiet or status == "FAIL":
            print(f"{status:<4}  {name:<16} {msg}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
