## 1. Tests first

- [ ] 1.1 Write failing tests in `tests/test_check_change.py` (`HookTest`): `test_stop_hook_size_blocks_once_per_session`, `test_stop_hook_non_actionable_only_system_message`, `test_stop_hook_sanitizes_untrusted_text`, `test_stop_hook_silent_paths` (clean tree, and no warnings), `test_installed_hook_matches_recorded_sha`; `test_stop_hook_blocks_then_gives_up` stays as the "failures unchanged" test
- [ ] 1.2 Write failing `test_quiet_prints_grandfather_warnings`

## 2. Build

- [ ] 2.1 `QUIET_WARN` in `check_change.py`; 1.2 passes
- [ ] 2.2 Write the new hook to `openspec/changes/stop-hook-warnings/stop-check.sh`, and record its sha256 here and in the PR body
- [ ] 2.3 **Human:** check the sha256, read the `git diff --no-index` against the installed hook, then `cp` it to `.claude/hooks/stop-check.sh`; 1.1 passes
- [ ] 2.4 Update docs/lifecycle.md, ADR 0004 (warnings: the user every time, the agent once for size), and docs/security.md (marker gaming, untrusted text)
- [ ] 2.5 Run the full suite and `scripts/check-change.sh --stage hook`. In a real Claude Code session, observe one Stop with a size warning (block, then `systemMessage` on the next stop). Record as `Evidence:`

## 3. Archive

- [ ] 3.1 Delete the proposed `stop-check.sh` from the change folder, archive, and confirm `openspec validate --all --strict` passes
