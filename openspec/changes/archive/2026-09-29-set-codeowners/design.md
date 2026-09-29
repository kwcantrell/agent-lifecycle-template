# Design: set code owners

Revised after the panel (see panel.md). Finding ids are given in brackets.

## Decisions

1. **Separate the template from this repo's own file.** init.sh renders
   `scripts/templates/CODEOWNERS.tmpl` into the target. It never copies this repo's
   `.github/CODEOWNERS` and never runs `place` on the template, so `@OWNER` can't reach a target
   verbatim. This matches `lifecycle.commands`: this repo's own values are never carried into a
   target. [m2]
   - Alternatives considered: (a) sed this repo's file, replacing `@kwcantrell`, which couples the
     installer to one handle; (b) a heredoc in init.sh, which puts data in code. Both keep the
     path list in a second place too, so the template file wins on clarity.
2. **Validate the owner before any write.** The accepted forms are `@user`, `@org/team`, or an
   email address. The patterns are `^@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:/[A-Za-z0-9._-]+)?$`
   and `^[^@\s]+@[^@\s]+\.[^@\s]+$`, each a single line. Anything else exits non-zero before any
   file is touched. When `gh` is installed and authenticated, init.sh checks that a `@user`
   resolves (`gh api users/<name>`) and warns if it doesn't. Teams and emails aren't looked up.
   [C1, C2]
3. **Render with Python, not sed.** A literal `str.replace` writes to a temp file in the target's
   `.github/`, then moves it into place, so there are no metacharacters and no half-written file.
   [C1, m1]
4. **Never write when any CODEOWNERS exists.** GitHub reads the first of `.github/`, the repo
   root and `docs/`. If any exists, init.sh writes nothing and never edits it (the old
   unconditional `sed -i` is removed). It lists the file under "skipped" and prints the lifecycle
   paths to add by hand under "Next steps". [M2]
5. **Collect every input before any write.** Arguments are parsed and validated first: a flag
   missing its value, or one whose value starts with `--`, is an error. Interactive prompts
   (commands, globs, owner) run next, then the writes. Interactive mode requires stdin to be a
   terminal. Otherwise init.sh runs non-interactively, so EOF can't abort it mid-install.
   `--owner` alone no longer suppresses prompts, and command flags alone no longer skip the
   owner prompt. [M1, M3, M4]
6. **No owner means skip, loudly.** A blank prompt answer, or non-interactive without `--owner`,
   writes no CODEOWNERS. The warning is repeated as the first "Next steps" item. The exit code
   stays 0, since the install otherwise succeeded, but `--dry-run` shows the outcome. [M4]
7. **Dry-run reports CODEOWNERS.** It prints one of: `would render .github/CODEOWNERS for <owner>`,
   `would skip CODEOWNERS: <path> exists`, `would skip CODEOWNERS: no owner`, or
   `CODEOWNERS depends on the owner prompt`. [M3]
8. **Hermetic init tests.** `tests/test_init.py` puts a stub `openspec` first on PATH. The stub
   creates `openspec/config.yaml` and the specs/changes dirs. Tests need only python3 and PyYAML,
   the same as the gate checker, with no network. [M5]
9. **State the solo-owner gap.** `docs/security.md` Known gaps: with one collaborator, code
   owner review is met through admin bypass on PRs. Anything holding the admin's token, an agent
   included, can bypass it. Real separation needs a second reviewer. [M7]

## Assumptions

| Assumption | Command | Observed |
| --- | --- | --- |
| `@OWNER` appears only in CODEOWNERS (rules and header comment) and init.sh | `grep -rn '@OWNER' --exclude-dir=.git . \| grep -v openspec/changes` | `.github/CODEOWNERS` (lines 2-11), `scripts/init.sh` (77, 119) |
| Nothing else references CODEOWNERS or scripts/templates | `grep -rln CODEOWNERS scripts .github/workflows` | `scripts/init.sh` only |
| Ruleset requires code owner review with 1 approval | `gh api .../rulesets/24211447 --jq '.rules[]\|select(.type=="pull_request").parameters'` | `require_code_owner_review: true`, `required_approving_review_count: 1` |
| Admin bypass is PR-only | `gh api .../rulesets/24211447 --jq .bypass_actors` | `[{"actor_id":5,"actor_type":"RepositoryRole","bypass_mode":"pull_request"}]` |
| `kwcantrell` is the only collaborator, with write | `gh api .../collaborators --jq '.[]\|[.login,.permissions.push]'` | `["kwcantrell",true]` |
| sed rendering breaks on metacharacters | `sed "s#@OWNER#@a#b#g"` / `sed "s#@OWNER#a&b#g"` | `unknown option to 's'` / `a@OWNERb` |
