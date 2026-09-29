## 1. Tests first

- [ ] 1.1 Write `tests/test_init.py` with a stub `openspec` on PATH, with failing tests `test_owner_renders`, `test_no_owner_skips_with_warning`, `test_invalid_owner_rejected_before_writes` (`acme`, `@a#b`, newline), `test_existing_codeowners_kept` (`.github/`, root, `docs/`), `test_dry_run_reports_codeowners` and `test_owner_flag_missing_value`
- [ ] 1.2 Write failing `test_repo_codeowners_names_owner` in `tests/test_init.py`: this repo's CODEOWNERS has no `@OWNER` and `@kwcantrell` on every lifecycle path

## 2. Installer

- [ ] 2.1 Add `scripts/templates/CODEOWNERS.tmpl`, then make 1.1 pass: parse and validate args first, prompt only on a tty, render with Python via a temp file, skip when any CODEOWNERS exists, report in dry-run, drop the `sed -i`
- [ ] 2.2 Update the init.sh `--help` text and "Next steps" (CODEOWNERS outcome first)

## 3. This repo and docs

- [ ] 3.1 Make 1.2 pass: set `.github/CODEOWNERS` to `@kwcantrell` and update its header comment
- [ ] 3.2 Add the solo-owner bypass gap to `docs/security.md` Known gaps, and CODEOWNERS to `docs/lifecycle.md` Setup
- [ ] 3.3 Run `scripts/check-change.sh --stage hook` and record the result as `Evidence:` on each task
