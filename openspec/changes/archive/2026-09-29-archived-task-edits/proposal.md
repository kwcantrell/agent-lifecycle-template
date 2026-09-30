# Don't count tasks.md-only edits to existing archives as a change

Tier: 2
Tier reason: touches scripts/ (high-risk path); the gate checker is the lifecycle's enforcement.

Approved-by: Kalen 2026-09-29

## Why

Adopting the lifecycle into a repo with an OpenSpec history can leave archived changes with unticked
tasks: deferred, dropped, or owed to a human. `openspec validate --archived` (the `openspec` gate)
fails on them. The fix is to edit those archives' `tasks.md`, but no PR can carry that edit, because
the `change` gate treats every edited archive as the branch's change:
- **two or more** archives edited fail "one change per branch";
- **one** archive edited is resolved as the branch's change, and fails because a pre-lifecycle
  proposal has no `Tier:` line.

autologger-2 hit this while adopting: 26 tasks across six archives. Its edits sit on its unmerged
install branch, which already fails this gate.

The panel also found that the checker's changed-file list itself is unsafe:
- it splits git's output on whitespace, so a path containing a space becomes two paths;
- git's rename detection lists only a rename's destination, so a file moved out of a directory hides
  its deletion.

Both affect every gate that reads the changed-file list, not just this one.

## What Changes

- **Changed-file listing is exact.** The checker lists changed paths NUL-separated with rename
  detection off, so each path is read whole and a move shows as a delete plus an add. Every gate
  that reads the list benefits.
- **tasks.md-only edits to existing archives are not a change.** The `change` gate does not count
  an archived change directory when all of these hold:
  - its name has the archive form `YYYY-MM-DD-<id>`;
  - it exists on the merge-base;
  - its only difference from the merge-base is one in-place modification of its `tasks.md`, which
    stays a regular file.
- **Reviewers see it.** Every `change` result names the archives it didn't count.
- **Documented.** A new ADR 0016 records the rule and its incident. `docs/security.md` records the
  residual risk. `docs/lifecycle.md`'s checks table gains the exemption.

Everything else is counted as today:
- an edit to any other file in an archive;
- a `tasks.md` that is added, deleted, moved, or changed in type;
- an archive the branch creates;
- any archive edit when there is no merge-base.

## Decisions (owner, 2026-09-29, from the panel)

- **Approach:** harden this exemption, rather than skipping `--archived` validation for old archives.
- **False ticks** (panel F-4): accept, and document it as a residual. A tier 0 PR can tick archived
  tasks that weren't done. The `change` message lists the archives, CODEOWNERS covers
  `openspec/changes/`, and `docs/security.md` records the risk.

## Non-goals

- Changing `openspec validate --archived`. Edited archives must still validate.
- Checking what an archived `tasks.md` edit says. Human review is the control (see Decisions).
- Any other gate's logic, beyond reading an exact changed-file list.

## Capabilities

- Modified: `gate-checker`. It gains two requirements: "Changed paths are read exactly" and
  "Task-list edits to existing archives are not a change".

## Impact

- `scripts/lib/check_change.py`: about 40 lines (`changed_files`, `check_change`, and one helper).
- `tests/test_check_change.py`: two new test classes.
- Docs:
  - `docs/decisions/0016-archived-task-edits.md` (new);
  - `docs/security.md`, which gains one residual line;
  - `docs/lifecycle.md`, one row.
- On archive: `openspec/specs/gate-checker/spec.md`.
- Size: code well under the 400-line budget (tests and docs excluded).
