# Panel: adopt-installer

Tier: 2 · Two rounds, each with assumption tester (A), failure and abuse (F), scope and simplicity (S) as separate Sonnet subagents · Date: 2026-09-29

Round 1 reviewed a design that merged into the target's existing files. After 2 critical findings
there, and 4 in the earlier safe-adoption draft, the approver chose "propose, don't merge" and the
design was rewritten. Round 2 reviewed the rewrite. Findings are de-duplicated within each round.
None were declined.

## Round 1 (merge design)

- [x] [critical] R1-F-C1: `openspec init` ran between plan and apply, so the fresh-repo config was never verified and the install was half-written. Evidence: design order place, openspec init, apply. Resolved: the rewrite writes the fresh config as a new file before `openspec init`, which keeps it (verified), and runs openspec init only on untouched repos.
- [x] [critical] R1-F-C2: the clean-tree check hides ignored files, so gitignored AGENTS.md or settings.json would be overwritten with no git copy, and `git clean -fd` misses ignored files. Evidence: init.sh `git status --porcelain`. Resolved: the rewrite never writes existing paths (lexists covers ignored files) and undoes from a validated manifest.
- [x] [major] R1-F-M1: plan-to-apply tampering and TOCTOU; the token didn't cover staged content. Resolved: moot, since there is no plan file, no apply step and no token; one process.
- [x] [major] R1-F-M2: the settings union could silently widen posture (template allows, bypassPermissions, disableAllHooks), and hooks were wired while a `.claude/hooks` dir was skipped. Resolved: the proposal never adds template allows, risks are reported first, and hooks are wired only when their script was installed identical.
- [x] [major] R1-F-M3: symlinks and file modes were broken by `os.replace`. Resolved: no existing file is replaced; symlinked leaves count as existing; parents are realpath-checked.
- [x] [major] R1-A-M1: the overlap heuristic missed `:*` and path variants. Resolved: cut. Risky allows are reported by simple rules, and deny precedence is documented.
- [x] [major] R1-A-M2: a block scalar at EOF false-fails the value comparison. Resolved: cut. The config proposal is now a snippet with no verification.
- [x] [major] R1-A-M3 / R1-S-M3: no config existed to plan against before `openspec init`, and there were two install paths. Resolved: a single install process writes the fresh config itself.
- [x] [major] R1-A-M4: the token bound nothing, and no ask rule for `--adopt`. Resolved: moot; no `--adopt` flag, since nothing existing is modified.
- [x] [major] R1-S-M1: over budget. Resolved: the rewrite removes the token, overlap, reconcile and verification code.
- [x] [major] R1-S-M2: a new rule with no ADR. Resolved: ADR 0015 (task 2.4).
- [x] [major] R1-S-M4: scenarios weren't mapped to tests. Resolved: tasks 1.1 and 1.2 name one test per scenario.
- [x] [minor] R1 minors (hook-prefix spellings, duplicate-key loader traps, marker hardening, echoed target text, lint coverage, docs placement): resolved by the rewrite or by R2 fixes below.

## Round 2 (propose, don't merge)

- [x] [critical] R2-A-C1 / R2-F-C1: init.sh's final `sync-skills.sh` deletes a target's own `.agents/skills/*` and overwrites same-name skills. If the target has its own sync-skills.sh, that runs instead. Evidence: scratch repo -> only `risk-tier` left, content `new`. Resolved: design 2; the target's scripts never run, and skills are copied create-only into both skill dirs. Tests `test_existing_and_ignored_files_untouched`.
- [x] [major] R2-A-M2: `openspec init` rewrote an existing `.claude/skills/openspec-propose/SKILL.md`. Evidence: ` M .claude/skills/openspec-propose/SKILL.md`. Resolved: design 6; it runs only when no OpenSpec-generated files exist. Test `test_openspec_init_skipped_when_generated_files_exist`.
- [x] [major] R2-F-M1: directory-granular `place` skipped the template hooks when `.claude/hooks/` existed, yet the proposal wired them, so the guard failed open. The substring test also matched mere mentions. Resolved: design 2 and 8; per-file copy, wired only if installed identical, reference regex. Tests `test_differing_hook_not_wired`, `test_hooks_already_referenced`.
- [x] [major] R2-F-M2: undo ran `rm -rf` on unvalidated, agent-writable manifest lines, and directory entries removed later user files. Resolved: design 4; the lines are validated first, and directories are removed only when empty. Tests `test_undo_rejects_tampered_manifest`, `test_undo_keeps_user_files`.
- [x] [major] R2-F-M3 / R2-A-M3: the manifest missed CODEOWNERS, `mkdir -p` parents and failure paths, and undo left empty dirs. Resolved: design 2-4 and 10; everything is created through adopt.py and recorded after creation, and an ERR trap prints undo. Test `test_undo_restores_tree`.
- [x] [major] R2-F-M4: the untracked folder is seen by the gates and the Stop hook, and is easy to commit. Evidence: check_change.py lists untracked files. Resolved: design 5; the folder self-ignores (verified 0 lines for status, ls-files and add -A). Test `test_adoption_folder_ignored`.
- [x] [major] R2-A-M4: the realpath check was prone to the string-prefix bug (`/a/t4-evil`). Resolved: design 2's separator rule; test `test_realpath_sibling_prefix_rejected`.
- [x] [major] R2-S-M1: the gate-checker spec's managed_paths contract conflicts, and there was no MODIFIED delta. Resolved: `specs/gate-checker/spec.md` MODIFIED requirement.
- [x] [major] R2-S-M2: tests without scenarios, and scenarios without tests. Resolved: the spec gains scenarios for hooks referenced, differing hook, existing lifecycle, undo and ignore. Cut behaviours (verification) are removed.
- [x] [major] R2-S-M3: the size estimate didn't count deletions. Resolved: the proposal now says about 310, deletions counted; task 2.6 measures it.
- [x] [minor] R2-S-m1: cut the config verification, `settings.local.json` and "Would grant". Resolved: all three cut; the config becomes a snippet.
- [x] [minor] R2-S-m2: fresh-config assumption untested on a fresh repo. Resolved: verified with the real CLI (sha1sum OK for config, AGENTS.md and a foreign skill).
- [x] [minor] R2-F-m1: target strings were echoed raw, and an agent might apply the proposals. Resolved: design 9 strips control chars, and the README says it's for a human; the residual is stated in docs/security.md.
- [x] [minor] R2-A-m5: openspec-init eligibility must be decided before install writes the config. Resolved: design 6.
- [x] [minor] R2-A-m6: yaml.compose's int/str key false positive, and risk regex misses `:*`. Resolved: the duplicate check is cut with verification; the `:*` form is noted as not flagged (advisory report).
- [x] [minor] R2-S-m3: docs should describe the two-phase flow, and ADR 0015 should record unwired hooks by default. Resolved: design 11.
