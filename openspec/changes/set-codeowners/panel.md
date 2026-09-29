# Panel: set-codeowners

Tier: 2 · Reviewers: assumption tester (AT), failure and abuse (FA), scope and simplicity (SS), each a separate Sonnet subagent · Date: 2026-09-29

Findings were de-duplicated across reviewers; the tags show who raised each. All are resolved by
the revised design.md, spec and tasks. None were declined.

- [x] [critical] C1 (FA, SS, AT): the owner goes into `sed "s#@OWNER#${owner}#g"` unvalidated. `#` breaks sed, `&` writes `@OWNER` back, and a newline injects extra CODEOWNERS lines (e.g. `/* @attacker`). Evidence: `sed "s#@OWNER#a&b#g"` -> `a@OWNERb`. Resolved: design 2 (strict single-line validation before any write) and 3 (Python literal replace).
- [x] [critical] C2 (FA): malformed or unresolvable owners (`kalen`, typos) are written silently, a false-protection state. Resolved: design 2 (format validation, plus a `gh api users/` warning when gh is available).
- [x] [major] M1 (FA): `--owner` as the last arg hits `set -u`, `--owner --dry-run` swallows the flag, and a bad owner aborts after files are copied. Resolved: design 5 (parse and validate all args first).
- [x] [major] M2 (FA, AT): only `.github/CODEOWNERS` was probed, so a root or `docs/` file gets shadowed. `sed -i` edits a pre-existing file the design called "kept". Resolved: design 4 (probe all three, never write or edit), spec scenario "Existing CODEOWNERS kept".
- [x] [major] M3 (SS, AT): rendering order and dry-run weren't specified. The prompt ran after copying, and dry-run exited before the owner was known. Resolved: design 5 and 7, spec scenario "Dry run reports the outcome".
- [x] [major] M4 (FA, SS, AT): interactive vs non-interactive owner handling was unspecified, EOF on the prompt aborted under `set -e`, and a blank answer was unexplained. Resolved: design 5 (prompt only on a tty) and 6.
- [x] [major] M5 (SS, AT): no harness for init.sh tests, which need the openspec CLI. Resolved: design 8 (stub `openspec` on PATH), task 1.1.
- [x] [major] M6 (SS): tasks didn't name their tests, and the "Placeholder removed" scenario had no test. Resolved: tasks 1.1 and 1.2 name every test; 2.x and 3.1 point to them.
- [x] [major] M7 (FA, AT): the solo-owner admin bypass gap was undocumented. An agent holding the admin's token can bypass code owner review. Resolved: design 9, task 3.2.
- [x] [minor] m1 (FA): partial writes. Resolved: design 3 (temp file then move) and 5 (all inputs before any write).
- [x] [minor] m2 (SS): alternatives weren't compared. Resolved: design 1 now lists them.
- [x] [minor] m3 (SS): help text and Next steps didn't mention CODEOWNERS; neither did docs/lifecycle.md Setup. Resolved: tasks 2.2 and 3.2.
- [x] [minor] m4 (SS): task 2.2 said "paste into the PR" instead of `Evidence:` in tasks.md. Resolved: task 3.3.
- [x] [minor] m5 (AT): the assumption table missed the CODEOWNERS header comment and didn't verify `bypass_actors`. Resolved: the table is updated; `bypass_actors` is verified as PR-only.
