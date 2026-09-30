## 1. Tests first

- [ ] 1.1 Write failing unit tests in `tests/test_adopt.py`: `test_proposed_settings_merge`, `test_hooks_already_referenced` (quoted `$CLAUDE_PROJECT_DIR` form), `test_differing_hook_not_wired`, `test_risk_report`, `test_jsonc_settings_not_proposed`, `test_config_snippet_only_missing_sections`, `test_existing_lifecycle_lists_missing_keys`, `test_guide_blocks`, `test_undo_rejects_tampered_manifest` (`..`, `/etc`, `.git`, outside), `test_undo_keeps_user_files`, `test_realpath_sibling_prefix_rejected`
- [ ] 1.2 Write failing init tests in `tests/test_init.py`: `test_existing_and_ignored_files_untouched` (with `.agents/skills/mine`), `test_symlink_outside_repo_skipped`, `test_existing_adoption_folder_refused`, `test_adoption_folder_ignored`, `test_undo_restores_tree`, `test_unwired_hooks_first_next_step`, `test_openspec_init_skipped_when_generated_files_exist`, `test_fresh_install_writes_config` (with `managed_paths` including adopt.py). Update `test_init_sets_managed_paths` and `test_init_keeps_existing_managed_paths` per the modified gate-checker requirement

## 2. Build

- [ ] 2.1 `scripts/lib/adopt.py` (install, proposals, risks, undo) per design 1-9; 1.1 passes
- [ ] 2.2 `init.sh` per design 1, 6 and 10: delegate writes to adopt.py, drop the copy loop, re-dump, CODEOWNERS render and sync-skills call, trap ERR to print undo, gate openspec init; make the stub openspec create-only; 1.2 and every existing test pass
- [ ] 2.3 Extend `lifecycle.commands.lint` to `scripts/lib/*.py`
- [ ] 2.4 Add ADR 0015; docs/lifecycle.md Setup and "Adopting into a repo with its own lifecycle"; docs/security.md gaps; the README install section
- [ ] 2.5 Real check on a scratch clone of infisical at `e5886f4`: its existing files are byte-identical (`sha1sum -c`), `.agents/skills/adversarial-panel` is intact, the proposals and risks are printed, `git status` shows no `.lifecycle-adoption/`, and undo leaves `git status --porcelain --ignored` as before. /home/spark/infisical unchanged
- [ ] 2.6 Run the full suite, `scripts/check-change.sh --stage hook`, and `--only size` (under 400); record them as `Evidence:`

## 3. Archive

- [ ] 3.1 After archive, replace the placeholder Purpose of `openspec/specs/installer/spec.md`; `openspec validate --all --strict` passes
