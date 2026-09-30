## 1. Tests first

- [x] 1.1 Write failing unit tests in `tests/test_adopt.py`: `test_proposed_settings_merge`, `test_hooks_already_referenced` (quoted `$CLAUDE_PROJECT_DIR` form), `test_differing_hook_not_wired`, `test_risk_report`, `test_jsonc_settings_not_proposed`, `test_config_snippet_only_missing_sections`, `test_existing_lifecycle_lists_missing_keys`, `test_guide_blocks`, `test_undo_rejects_tampered_manifest` (`..`, `/etc`, `.git`, outside), `test_undo_keeps_user_files`, `test_realpath_sibling_prefix_rejected`
  Evidence: before adopt.py existed -> `ERROR: test_adopt` (module missing); after 2.1 -> `Ran 14 tests ... OK`
- [x] 1.2 Write failing init tests in `tests/test_init.py`: `test_existing_and_ignored_files_untouched` (with `.agents/skills/mine`), `test_symlink_outside_repo_skipped`, `test_existing_adoption_folder_refused`, `test_adoption_folder_ignored`, `test_undo_restores_tree`, `test_unwired_hooks_first_next_step`, `test_openspec_init_skipped_when_generated_files_exist`, `test_fresh_install_writes_config` (with `managed_paths` including adopt.py). Update `test_init_sets_managed_paths` and `test_init_keeps_existing_managed_paths` per the modified gate-checker requirement
  Evidence: before the build -> 8 FAIL (7 new adoption tests + the updated `test_init_sets_managed_paths`); the `InitFixture` split avoids re-running InitTest's tests

## 2. Build

- [x] 2.1 `scripts/lib/adopt.py` (install, proposals, risks, undo) per design 1-9; 1.1 passes
  Evidence: `python3 -m unittest tests.test_adopt` -> OK (14)
- [x] 2.2 `init.sh` per design 1, 6 and 10: delegate writes to adopt.py, drop the copy loop, re-dump, CODEOWNERS render and sync-skills call, trap ERR to print undo, gate openspec init; make the stub openspec create-only; 1.2 and every existing test pass
  Evidence: `python3 -m unittest discover -s tests` -> `Ran 84 tests ... OK`
- [x] 2.3 Extend `lifecycle.commands.lint` to `scripts/lib/*.py`
  Evidence: `scripts/check-change.sh --only commands` -> `PASS commands ran ['lint', 'test']` with `py_compile scripts/lib/*.py`
- [x] 2.4 Add ADR 0015; docs/lifecycle.md Setup and "Adopting into a repo with its own lifecycle"; docs/security.md gaps; the README install section
  Evidence: `ls docs/decisions/0015-adopt-by-proposal.md`; docs/lifecycle.md `### Adopting into a repo with its own lifecycle`; 2 docs/security.md gaps; README install text
- [x] 2.5 Real check on a scratch clone of infisical at `e5886f4`: its existing files are byte-identical (`sha1sum -c`), `.agents/skills/adversarial-panel` is intact, the proposals and risks are printed, `git status` shows no `.lifecycle-adoption/`, and undo leaves `git status --porcelain --ignored` as before. /home/spark/infisical unchanged
  Evidence: scratch clone at `e5886f4`: `sha1sum -c` of all original files -> all-identical; folder has settings.json (hooks PreToolUse+Stop, enabledPlugins kept, sandbox enabled), config snippet, both blocks, README; `git status` lists 0 folder entries; Next steps 1 = hooks not active; `adopt.py undo` -> `removed 50 path(s)`, `status --porcelain --ignored` identical, files identical. /home/spark/infisical: 0 status lines, still `b72d0aa`
- [x] 2.6 Run the full suite, `scripts/check-change.sh --stage hook`, and `--only size` (under 400); record them as `Evidence:`
  Evidence: `python3 -m unittest discover -s tests` -> OK (84); `scripts/check-change.sh --stage hook --quiet` -> rc=0; `--only size` -> `FAIL 577 changed lines > budget 400` (adopt.py 419 new, init.sh 135 lines moved out, README 7). The estimate of ~310 was wrong. Human chose `size-override` on 2026-09-29: the moved lines aren't new behaviour, and a split would ship an installer that still runs the target's sync-skills.sh.

## 3. Archive

- [ ] 3.1 After archive, replace the placeholder Purpose of `openspec/specs/installer/spec.md`; `openspec validate --all --strict` passes
