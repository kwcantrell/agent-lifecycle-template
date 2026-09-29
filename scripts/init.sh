#!/usr/bin/env bash
# Installs the agent lifecycle into an existing git repo. Never overwrites a file that exists;
# it reports what it skipped so a human can merge by hand.
#
#   scripts/init.sh [--dry-run] [--owner @user|@org/team|email] [--test CMD] [--lint CMD]
#                   [--typecheck CMD] [--audit CMD] [--build CMD] [--source-glob GLOB]... TARGET
#
# On a terminal it asks for whatever flags didn't give (stack-agnostic: no presets yet).
# Without an owner, CODEOWNERS is skipped; an existing CODEOWNERS is never touched.
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
dry=0 owner="" have_owner=0 target="" have_cmds=0
declare -A cmd=([test]="" [lint]="" [typecheck]="" [audit]="" [build]="")
src_globs=()

die() { echo "init: $*" >&2; exit 1; }
need_value() { [[ $# -ge 2 && -n "$2" && "$2" != --* ]] || die "$1 needs a value"; }

# Parse and validate everything before any prompt or write.
while (($#)); do
  case "$1" in
    --dry-run) dry=1 ;;
    --owner) need_value "$@"; owner="$2"; have_owner=1; shift ;;
    --test|--lint|--typecheck|--audit|--build) need_value "$@"; cmd[${1#--}]="$2"; have_cmds=1; shift ;;
    --source-glob) need_value "$@"; src_globs+=("$2"); shift ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    --*) die "unknown option $1" ;;
    *) target="$1" ;;
  esac
  shift
done

# A GitHub @user, @org/team, or an email, on one line. Anything else could inject CODEOWNERS rules.
valid_owner() {
  python3 -c '
import re, sys
o = sys.argv[1]
ok = re.fullmatch(r"@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:/[A-Za-z0-9._-]+)?", o) \
     or re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", o)
sys.exit(0 if ok else 1)' "$1"
}
check_owner() {
  valid_owner "$1" || die "owner '$1' is not a single @user, @org/team or email"
  if [[ "$1" =~ ^@[^/]+$ ]] && command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
    gh api "users/${1#@}" >/dev/null 2>&1 || echo "init: warning: GitHub user $1 not found" >&2
  fi
  return 0
}
((have_owner)) && check_owner "$owner"

[[ -n "$target" ]] || die "usage: init.sh [options] TARGET (see --help)"
target="$(cd "$target" && pwd)"
git -C "$target" rev-parse --git-dir >/dev/null 2>&1 || die "$target is not a git repo"
[[ -z "$(git -C "$target" status --porcelain)" ]] || die "$target has uncommitted changes; commit or stash first"
command -v python3 >/dev/null || die "python3 is required"
python3 -c 'import yaml' 2>/dev/null || die "PyYAML is required (pip install pyyaml)"
command -v openspec >/dev/null || die "OpenSpec is required (npm install -g @fission-ai/openspec@1.13.2)"

# Prompts run only on a terminal, only for what flags didn't give, and all before any write.
if ((!dry)) && [[ -t 0 ]]; then
  if ((!have_cmds)); then
    echo "Stack commands for the gates (leave blank to skip; edit openspec/config.yaml later):"
    for k in test lint typecheck audit build; do read -r -p "  $k: " "cmd[$k]" || true; done
    read -r -p "  source globs, space-separated (e.g. src/** lib/**): " -a src_globs || true
  fi
  if ((!have_owner)); then
    read -r -p "  CODEOWNERS owner (@user, @org/team or email; blank skips CODEOWNERS): " owner || true
    [[ -z "$owner" ]] || check_owner "$owner"
  fi
fi

# GitHub uses the first CODEOWNERS of .github/, root, docs/. If any exists, we never write one.
existing_codeowners=""
for loc in .github/CODEOWNERS CODEOWNERS docs/CODEOWNERS; do
  if [[ -e "$target/$loc" ]]; then existing_codeowners="$loc"; break; fi
done
if [[ -n "$existing_codeowners" ]]; then codeowners="exists"
elif [[ -n "$owner" ]]; then codeowners="render"
elif ((dry)) && [[ -t 0 ]]; then codeowners="prompt"
else codeowners="none"; fi

copied=() skipped=()
place() {  # place SRC_REL [DEST_REL]
  local src="$here/$1" dest="$target/${2:-$1}"
  if [[ -e "$dest" ]]; then skipped+=("${2:-$1}"); return; fi
  copied+=("${2:-$1}")
  ((dry)) && return
  mkdir -p "$(dirname "$dest")"
  cp -R "$src" "$dest"
}

# CODEOWNERS is rendered from scripts/templates/, never copied: this repo's owners stay here.
for f in AGENTS.md CLAUDE.md .pre-commit-config.yaml \
         .claude/settings.json .claude/hooks \
         .claude/skills/adversarial-panel .claude/skills/consistency-read .claude/skills/risk-tier \
         .github/workflows/lifecycle.yml .github/workflows/release.yml .github/dependabot.yml \
         .github/pull_request_template.md \
         scripts/check-change.sh scripts/sync-skills.sh scripts/lib/check_change.py \
         docs/lifecycle.md docs/security.md docs/templates; do
  place "$f"
done
for adr in "$here"/docs/decisions/*.md; do
  place "docs/decisions/$(basename "$adr")"
done

if ((dry)); then
  printf 'would copy:\n'; printf '  %s\n' "${copied[@]}"
  ((${#skipped[@]})) && { printf 'would skip (exists):\n'; printf '  %s\n' "${skipped[@]}"; }
  [[ -d "$target/openspec" ]] && echo "would merge the lifecycle block into openspec/config.yaml" \
                              || echo "would run: openspec init --tools claude,codex"
  case "$codeowners" in
    render) echo "would render .github/CODEOWNERS for $owner" ;;
    exists) echo "would skip CODEOWNERS: $existing_codeowners exists" ;;
    prompt) echo "CODEOWNERS depends on the owner prompt" ;;
    none)   echo "would skip CODEOWNERS: no owner" ;;
  esac
  exit 0
fi

# OpenSpec: generate its own skills rather than copying them, so `openspec update` owns them.
if [[ ! -d "$target/openspec" ]]; then
  (cd "$target" && openspec init --tools claude,codex --no-animation --no-copilot-cloud .)
fi

# Merge the template's config into the target's, keeping anything the target already set.
export LC_TEST="${cmd[test]}" LC_LINT="${cmd[lint]}" LC_TYPECHECK="${cmd[typecheck]}" \
       LC_AUDIT="${cmd[audit]}" LC_BUILD="${cmd[build]}" LC_SRC="${src_globs[*]:-}"
python3 - "$here/openspec/config.yaml" "$target/openspec/config.yaml" <<'PY'
import os, sys, yaml
tpl_path, dst_path = sys.argv[1:]
tpl = yaml.safe_load(open(tpl_path))
dst = yaml.safe_load(open(dst_path)) or {}
notes = []
for key in ("rules", "operations"):
    for section, items in (tpl.get(key) or {}).items():
        target = dst.setdefault(key, {}).setdefault(section, {} if key == "operations" else [])
        if key == "operations":
            target = target.setdefault("guidance", [])
            items = items["guidance"]
        target.extend(i for i in items if i not in target)
if "context" not in dst:
    dst["context"] = tpl["context"]
else:
    notes.append("kept your `context:`; add the lifecycle sentence from the template by hand")
lc = dst.setdefault("lifecycle", {})
defaults = dict(tpl["lifecycle"])
defaults["commands"] = {k: "" for k in defaults["commands"]}  # the template's own; never copied
defaults["source_globs"] = []
# Exact files init.sh installs: vendored code, not the target's source.
defaults["managed_paths"] = ["scripts/check-change.sh", "scripts/sync-skills.sh",
                             "scripts/lib/check_change.py", ".claude/hooks/guard-approval.sh",
                             ".claude/hooks/stop-check.sh"]
for k, v in defaults.items():
    lc.setdefault(k, v)
for k in ("test", "lint", "typecheck", "audit", "build"):
    if os.environ.get(f"LC_{k.upper()}"):
        lc["commands"][k] = os.environ[f"LC_{k.upper()}"]
if os.environ.get("LC_SRC"):
    lc["source_globs"] = os.environ["LC_SRC"].split()
with open(dst_path, "w") as f:
    f.write("# Merged by agent-lifecycle-template scripts/init.sh. See AGENTS.md.\n")
    yaml.safe_dump(dst, f, sort_keys=False, width=100)
for n in notes:
    print("note:", n)
PY

if [[ "$codeowners" == render ]]; then
  # Literal replace into a temp file, then move: no sed metacharacters, no half-written file.
  python3 - "$here/scripts/templates/CODEOWNERS.tmpl" "$target/.github/CODEOWNERS" "$owner" <<'PY'
import os, sys, tempfile
tmpl, dest, owner = sys.argv[1:]
text = open(tmpl).read().replace("@OWNER", owner)
os.makedirs(os.path.dirname(dest), exist_ok=True)
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest))
with os.fdopen(fd, "w") as f:
    f.write(text)
os.chmod(tmp, 0o644)
os.replace(tmp, dest)
PY
  copied+=(".github/CODEOWNERS")
elif [[ "$codeowners" == exists ]]; then
  skipped+=("$existing_codeowners")
fi
(cd "$target" && scripts/sync-skills.sh)

printf 'copied:\n'; printf '  %s\n' "${copied[@]}"
((${#skipped[@]})) && { printf 'skipped (already exists, merge by hand):\n'; printf '  %s\n' "${skipped[@]}"; }

owned_paths() { grep -v '^#' "$here/scripts/templates/CODEOWNERS.tmpl" | sed 's/^/       /'; }
echo
echo "Next steps (a human does these; see docs/lifecycle.md#setup):"
case "$codeowners" in
  render) echo "  1. CODEOWNERS names $owner. Keep \"Require review from Code Owners\" on in the main ruleset." ;;
  exists) echo "  1. CODEOWNERS: $existing_codeowners was kept. Add these lifecycle paths to it by hand:"
          owned_paths ;;
  *)      echo "  1. CODEOWNERS was NOT written (no owner), so code owner review protects nothing."
          echo "     Rerun with --owner, or create .github/CODEOWNERS with these paths:"
          owned_paths ;;
esac
echo '  2. Add your toolchain setup to .github/workflows/lifecycle.yml and release.yml ("Stack setup").'
echo "  3. Main ruleset: require a PR, code owner review, and the gates / secrets / dependency-review checks."
echo "  4. Turn on secret scanning push protection and the dependency graph."
echo "  5. pre-commit install --hook-type pre-commit --hook-type pre-push"
echo "  6. Run scripts/check-change.sh and commit the result as a tier 2 change."
