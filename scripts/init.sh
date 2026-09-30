#!/usr/bin/env bash
# Installs the agent lifecycle into an existing git repo. Never overwrites a file that exists;
# it reports what it skipped so a human can merge by hand.
#
#   scripts/init.sh [--dry-run] [--owner @user|@org/team|email] [--test CMD] [--lint CMD]
#                   [--typecheck CMD] [--audit CMD] [--build CMD] [--source-glob GLOB]... TARGET
#
# On a terminal it asks for whatever flags didn't give (stack-agnostic: no presets yet).
# It only creates files; for files the target already has it writes proposals into
# .lifecycle-adoption/ for a human. Without an owner, CODEOWNERS is skipped.
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
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
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

# Every write goes through adopt.py: create-only, recorded in .lifecycle-adoption/MANIFEST, with
# proposals for files the target already has (ADR 0015).
owner_pending=0
((dry)) && [[ -t 0 && -z "$owner" ]] && owner_pending=1
commands_json="$(python3 -c 'import json,sys; print(json.dumps(dict(zip(sys.argv[1::2], sys.argv[2::2]))))' \
  test "${cmd[test]}" lint "${cmd[lint]}" typecheck "${cmd[typecheck]}" audit "${cmd[audit]}" build "${cmd[build]}")"
args=(install --target "$target" --template "$here" --commands "$commands_json")
[[ -n "$owner" ]] && args+=(--owner "$owner")
((owner_pending)) && args+=(--owner-pending)
((dry)) && args+=(--dry-run)
for g in "${src_globs[@]}"; do args+=(--source-glob "$g"); done
((dry)) || trap 'echo "init: install incomplete. Undo: python3 $here/scripts/lib/adopt.py undo --target $target" >&2' ERR
python3 "$here/scripts/lib/adopt.py" "${args[@]}"
