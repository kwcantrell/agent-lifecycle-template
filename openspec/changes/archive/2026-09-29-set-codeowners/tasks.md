## 1. Tests first

- [x] 1.1 Write `tests/test_init.py` with a stub `openspec` on PATH, with failing tests `test_owner_renders`, `test_no_owner_skips_with_warning`, `test_invalid_owner_rejected_before_writes` (`acme`, `@a#b`, newline), `test_existing_codeowners_kept` (`.github/`, root, `docs/`), `test_dry_run_reports_codeowners` and `test_owner_flag_missing_value`
  Evidence: `python3 -m unittest tests.test_init` before the fix -> `FAILED (failures=16, errors=1)`
- [x] 1.2 Write failing `test_repo_codeowners_names_owner` in `tests/test_init.py`: this repo's CODEOWNERS has no `@OWNER` and `@kwcantrell` on every lifecycle path
  Evidence: after 2.1, `python3 -m unittest tests.test_init` -> only `FAIL: test_repo_codeowners_names_owner`

## 2. Installer

- [x] 2.1 Add `scripts/templates/CODEOWNERS.tmpl`, then make 1.1 pass: parse and validate args first, prompt only on a tty, render with Python via a temp file, skip when any CODEOWNERS exists, report in dry-run, drop the `sed -i`
  Evidence: `python3 -m unittest tests.test_init` -> 8 of 9 pass; real run `init.sh --owner $'@a\n/* @attacker' t2` -> `not a single @user, @org/team or email`, rc=1, 0 files written
- [x] 2.2 Update the init.sh `--help` text and "Next steps" (CODEOWNERS outcome first)
  Evidence: real run `init.sh --owner @kwcantrell --test true t2` -> `1. CODEOWNERS names @kwcantrell. Keep "Require review from Code Owners" on`

## 3. This repo and docs

- [x] 3.1 Make 1.2 pass: set `.github/CODEOWNERS` to `@kwcantrell` and update its header comment
  Evidence: `python3 -m unittest discover -s tests` -> `Ran 32 tests ... OK`
- [x] 3.2 Add the solo-owner bypass gap to `docs/security.md` Known gaps, and CODEOWNERS to `docs/lifecycle.md` Setup
  Evidence: `grep -c "bypass on PRs" docs/security.md` -> 1; `grep -c 'renders \`.github/CODEOWNERS\`' docs/lifecycle.md` -> 1
- [x] 3.3 Run `scripts/check-change.sh --stage hook` and record the result as `Evidence:` on each task
  Evidence: `scripts/check-change.sh --stage hook` -> all PASS (openspec, workflows, skills-sync, guide-size, change tier 2, risk-floor, evidence, commands)
