## 1. Tests first

- [x] 1.1 Write failing tests in `tests/test_check_change.py` (`HookTest`): `test_stop_hook_size_blocks_once_per_session`, `test_stop_hook_non_actionable_only_system_message`, `test_stop_hook_sanitizes_untrusted_text`, `test_stop_hook_silent_paths` (clean tree, and no warnings), `test_installed_hook_matches_recorded_sha`; `test_stop_hook_blocks_then_gives_up` stays as the "failures unchanged" test
  Evidence: against the current hook -> 4 ERROR (no JSON output) + `test_installed_hook_matches_recorded_sha` FAIL; `test_stop_hook_silent_paths` passed as a regression guard
- [x] 1.2 Write failing `test_quiet_prints_grandfather_warnings`
  Evidence: before `QUIET_WARN` -> FAIL (no `WARN change` under --quiet)

## 2. Build

- [x] 2.1 `QUIET_WARN` in `check_change.py`; 1.2 passes
  Evidence: `python3 -m unittest ...test_quiet_prints_grandfather_warnings` -> OK
- [x] 2.2 Write the new hook to `openspec/changes/stop-hook-warnings/stop-check.sh`, and record its sha256 here and in the PR body
  Evidence: stop-check.sh sha256: aeacc63dad27525758aa431b0a32772e532caf71716ff5b5d0787ac677bf22dd
  Pre-verified in throwaway repos (the proposed hook committed into each fixture's base): StopHookWarningTest (6) plus the 3 existing HookTest tests -> `Ran 9 tests ... OK`
- [x] 2.3 **Human:** check the sha256, read the `git diff --no-index` against the installed hook, then `cp` it to `.claude/hooks/stop-check.sh`; 1.1 passes
  Evidence: the human ran `git diff --no-index` (reviewed), `sha256sum` -> `aeacc63d...bf22dd` (matches), then `cp`; the installed `.claude/hooks/stop-check.sh` sha256 is the same; `test_installed_hook_matches_recorded_sha` passes
- [x] 2.4 Update docs/lifecycle.md, ADR 0004 (warnings: the user every time, the agent once for size), and docs/security.md (marker gaming, untrusted text)
  Evidence: ADR 0004 `Amended 2026-09-29 (stop-hook-warnings)`; docs/lifecycle.md Stop hook sentence; docs/security.md marker and untrusted-text gap
- [x] 2.5 Run the full suite and `scripts/check-change.sh --stage hook`. In a real Claude Code session, observe one Stop with a size warning (block, then `systemMessage` on the next stop). Record as `Evidence:`
  Evidence: `python3 -m unittest discover -s tests` -> `Ran 140 tests ... OK`. Live session, with a 450-line untracked probe (`WARN size 516 changed lines > budget 400`). First stop: blocked once; the reason began with the instruction, then "Untrusted check output follows", and the backticks were sanitized to `?`. Second stop: not blocked; the human confirmed seeing the systemMessage. Probe removed

## 3. Archive

- [ ] 3.1 Delete the proposed `stop-check.sh` from the change folder, archive, and confirm `openspec validate --all --strict` passes
