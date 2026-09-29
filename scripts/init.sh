#!/usr/bin/env bash
# Installs the agent lifecycle into an existing git repo. Never overwrites a file that exists;
# it reports what it skipped so a human can merge by hand.
#
#   scripts/init.sh [--dry-run] [--owner @org/team] [--test CMD] [--lint CMD]
#                   [--typecheck CMD] [--audit CMD] [--build CMD] [--source-glob GLOB]... TARGET
#
# Without the command flags it asks for them (stack-agnostic: no presets yet).
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
dry=0 owner="" target="" interactive=1
declare -A cmd=([test]="" [lint]="" [typecheck]="" [audit]="" [build]="")
src_globs=()

while (($#)); do
  case "$1" in
    --dry-run) dry=1 ;;
    --owner) owner="$2"; shift ;;
    --test|--lint|--typecheck|--audit|--build) cmd[${1#--}]="$2"; interactive=0; shift ;;
    --source-glob) src_globs+=("$2"); shift ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) target="$1" ;;
  esac
  shift
done

die() { echo "init: $*" >&2; exit 1; }
[[ -n "$target" ]] || die "usage: init.sh [options] TARGET (see --help)"
target="$(cd "$target" && pwd)"
git -C "$target" rev-parse --git-dir >/dev/null 2>&1 || die "$target is not a git repo"
[[ -z "$(git -C "$target" status --porcelain)" ]] || die "$target has uncommitted changes; commit or stash first"
command -v python3 >/dev/null || die "python3 is required"
python3 -c 'import yaml' 2>/dev/null || die "PyYAML is required (pip install pyyaml)"
command -v openspec >/dev/null || die "OpenSpec is required (npm install -g @fission-ai/openspec@1.13.2)"

copied=() skipped=()
place() {  # place SRC_REL [DEST_REL]
  local src="$here/$1" dest="$target/${2:-$1}"
  if [[ -e "$dest" ]]; then skipped+=("${2:-$1}"); return; fi
  copied+=("${2:-$1}")
  ((dry)) && return
  mkdir -p "$(dirname "$dest")"
  cp -R "$src" "$dest"
}

for f in AGENTS.md CLAUDE.md .pre-commit-config.yaml \
         .claude/settings.json .claude/hooks \
         .claude/skills/adversarial-panel .claude/skills/consistency-read .claude/skills/risk-tier \
         .github/workflows/lifecycle.yml .github/workflows/release.yml .github/dependabot.yml \
         .github/CODEOWNERS .github/pull_request_template.md \
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
  exit 0
fi

# OpenSpec: generate its own skills rather than copying them, so `openspec update` owns them.
if [[ ! -d "$target/openspec" ]]; then
  (cd "$target" && openspec init --tools claude,codex --no-animation --no-copilot-cloud .)
fi

if ((interactive)); then
  echo "Stack commands for the gates (leave blank to skip; edit openspec/config.yaml later):"
  for k in test lint typecheck audit build; do read -r -p "  $k: " "cmd[$k]"; done
  read -r -p "  source globs, space-separated (e.g. src/** lib/**): " -a src_globs
  [[ -n "$owner" ]] || read -r -p "  CODEOWNERS owner (e.g. @org/maintainers): " owner
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

if [[ -n "$owner" ]]; then
  sed -i.bak "s#@OWNER#${owner}#g" "$target/.github/CODEOWNERS" && rm -f "$target/.github/CODEOWNERS.bak"
fi
(cd "$target" && scripts/sync-skills.sh)

printf 'copied:\n'; printf '  %s\n' "${copied[@]}"
((${#skipped[@]})) && { printf 'skipped (already exists, merge by hand):\n'; printf '  %s\n' "${skipped[@]}"; }
cat <<'EOF'

Next steps (a human does these; see docs/lifecycle.md#setup):
  1. Add your toolchain setup to .github/workflows/lifecycle.yml and release.yml ("Stack setup").
  2. Main ruleset: require a PR, code owner review, and the gates / secrets / dependency-review checks.
  3. Turn on secret scanning push protection and the dependency graph.
  4. pre-commit install --hook-type pre-commit --hook-type pre-push
  5. Run scripts/check-change.sh and commit the result as a tier 2 change.
EOF
