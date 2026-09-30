# Panel: stop-hook-warnings

Tier: 2 · Reviewers: assumption tester (A), failure and abuse (F), scope and simplicity (S), each a separate Sonnet subagent · Date: 2026-09-29

Findings are de-duplicated. All are resolved in the revised proposal, design, spec and tasks.
None were declined.

- [x] [major] A-M1 / F-M1: the size WARN embeds its line count, so a hash of the text re-arms the block on every edit, and the warn path had no cap. Evidence: check_change.py `f"{total} changed lines > budget ..."`. Resolved: design 2, the marker is keyed on the check name, once per session; test `test_stop_hook_size_blocks_once_per_session`.
- [x] [major] A-M2: an unguarded `grep '^WARN'` exits 1 with no matches and kills the hook under `set -e`. Evidence: bash repro, rc=1. Resolved: design 1 (`|| true`); test `test_stop_hook_silent_paths`.
- [x] [major] F-M2: warning text is repo-controlled and would enter the model's context as a hook reason (prompt injection). Resolved: design 3 (safe charset, caps, instruction first, untrusted delimiter); test `test_stop_hook_sanitizes_untrusted_text`.
- [x] [major] F-M3: the human copy comes from an agent-writable path with no review. Resolved: design 6, where the sha256 is recorded in tasks and the PR and checked before the copy, the diff is read, a test checks the installed sha, and the proposed copy is deleted before archive.
- [x] [major] S-M1: "block once" wasn't argued against `systemMessage` only, and non-actionable warnings would cost turns. Resolved: design 2, only the actionable size warning blocks; the rest are `systemMessage` only.
- [x] [major] S-M2: installer propagation wasn't covered. Resolved: design 9, no change; existing targets keep their hook until the update change (a non-goal).
- [x] [minor] S-m1: scenario-to-test mapping. Resolved: task 1.1 names one test per scenario; the existing gives-up test covers "failures unchanged".
- [x] [minor] S-m4: stray proposed copy and divergence. Resolved: design 6, deleted before archive, and the installed sha is tested.
- [x] [minor] S-m5: new capability vs gate-checker. Resolved: design 8, the requirement goes in gate-checker.
- [x] [minor] S-m6 / F-m4: interaction with the failure counter, and a failed marker write. Resolved: design 1, where a pass clears the counter and marker failure falls back to `systemMessage` only.
- [x] [minor] F-m1: the marker can be gamed like the counter. Resolved: design 5, stated; `systemMessage` to the human is unconditional.
- [x] [minor] F-m2: noisy blocks train the agent to ignore them. Resolved: design 2, where only actionable warnings block, once.
- [x] [minor] A-m3: `session_id` and `TMPDIR` stability unverified; a missing session id meant a shared key. Resolved: design 4, where no session id means no block; task 2.5 verifies it in a real session.
- [x] [minor] A-m4: WARN format and quiet set. Resolved: design 7, single-line WARNs stated.
- [x] [minor] A-m5: stdout JSON cleanliness. Resolved: design 1, where all output goes through one python3 call.
- [x] [minor] A-m6: Stop JSON semantics come from a summarizing fetch. Resolved: task 2.5 observes both the block and `systemMessage` in a real session.
